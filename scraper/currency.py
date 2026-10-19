"""Exchange rates (Bank of Canada Valet API) and currency-driven price signals.

1. fx_update(): daily official Bank of Canada rates (CAD per 1 USD / EUR / GBP / JPY), history kept in data/fx.json,
   with 7- and 30-day changes. Source: https://www.bankofcanada.ca/valet/ (free, no key). BoC rates are indicative
   averages, not what a card or bank will charge you.
2. currency_gap(): where the same model has a US-dollar offer (data/us-offers.json, filled by hand, by an affiliate
   product feed, or by the eBay Browse API when keys exist), estimate the landed CAD cost
   (price x rate + shipping + brokerage + GST) and flag it when it is meaningfully below the cheapest Canadian price.
3. rate_moved(): when CAD moved more than RATE_MOVE_MIN against USD over 30 days, flag Canadian new-gear prices that
   have not changed in that window: they may adjust. Never a promise.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse

from .http import fetch

VALET = "https://www.bankofcanada.ca/valet/observations/{series}/json"
SERIES = {"USD": "FXUSDCAD", "EUR": "FXEURCAD", "GBP": "FXGBPCAD", "JPY": "FXJPYCAD"}
FX_KEEP_DAYS = 800
RATE_MOVE_MIN = 0.025          # 2.5% over 30 days
RATE_MOVE_MIN_TRACKED_DAYS = 14  # need this many days of our own new-price history before saying "hasn't changed"
GAP_MIN_PCT = 0.05             # landed US price must be >= 5% below the cheapest Canadian price ...
GAP_MIN_CAD = 50               # ... and at least $50 cheaper
DEFAULT_SHIP_CAD = 40.0        # estimate when an offer does not state shipping to Canada
DEFAULT_BROKERAGE_CAD = 25.0   # courier brokerage/handling estimate (UPS/FedEx/DHL); ~0 for postal or DDP shipments
GST = 0.05                     # federal GST collected at the border; HST provinces pay 13-15% instead (see TAX_NOTE)
TAX_NOTE = ("Estimate uses 5% GST (AB, BC, MB, SK, QC, territories; BC/MB/SK/QC provincial sales tax may also apply). "
            "HST provinces pay 13% (ON) or 15% (NB, NL, NS, PE) instead.")
DUTY_NOTE = ("Most cameras and lenses enter Canada duty-free, but check the item's tariff code; couriers usually add a "
             "brokerage fee, estimated here, unless the seller ships duty-paid (DDP).")


def _pct(a: float, b: float) -> float:
    return round(a / b - 1, 4)


def _value_on_or_before(hist: list[list], day: str):
    best = None
    for d, v in hist:
        if d <= day:
            best = (d, v)
        else:
            break
    return best


def summarize(hist: list[list]) -> dict | None:
    """hist: [[YYYY-MM-DD, rate], ...] sorted. Returns latest rate and 7/30-day % changes (CAD per unit)."""
    if not hist:
        return None
    d, v = hist[-1]
    out = {"date": d, "rate": v}
    for n in (7, 30):
        past = _value_on_or_before(hist, (dt.date.fromisoformat(d) - dt.timedelta(days=n)).isoformat())
        out[f"chg_{n}d"] = _pct(v, past[1]) if past else None
        out[f"from_{n}d"] = past[1] if past else None
    return out


def describe(code: str, s: dict, n: int = 30) -> str:
    """Plain-English direction. Rate is CAD per 1 unit, so a higher rate = weaker CAD."""
    c = s.get(f"chg_{n}d")
    if c is None:
        return f"Not enough {code}/CAD history yet for a {n}-day change."
    if abs(c) < 0.001:
        return f"The Canadian dollar is flat against the {code} over {n} days."
    word = "weakened" if c > 0 else "strengthened"
    return f"The Canadian dollar {word} {abs(c) * 100:.1f}% against the {code} over {n} days."


def fx_update(prev: dict, today: str, now: str) -> dict:
    start = (dt.date.fromisoformat(today) - dt.timedelta(days=120)).isoformat()
    url = VALET.format(series=",".join(SERIES.values())) + "?" + urllib.parse.urlencode({"start_date": start})
    out = {"source": "Bank of Canada daily exchange rates (Valet API)", "source_url": "https://www.bankofcanada.ca/rates/exchange/daily-exchange-rates/",
           "terms_url": "https://www.bankofcanada.ca/terms/", "note": "Indicative daily average rates, published around 4:30 p.m. ET on business days. Banks and card issuers charge more.",
           "fetched_at": now, "series": {}, "latest": {}, "error": None}
    obs = []
    try:
        obs = json.loads(fetch(url, check_robots=True)).get("observations", [])
    except Exception as e:  # keep yesterday's history; never break the daily run
        out["error"] = f"{type(e).__name__}: {e}"
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=FX_KEEP_DAYS)).isoformat()
    for code, sid in SERIES.items():
        hist = {d: v for d, v in ((prev.get("series") or {}).get(code) or {}).get("history", [])}
        for o in obs:
            v = (o.get(sid) or {}).get("v")
            if v not in (None, ""):
                hist[o["d"]] = float(v)
        h = sorted([d, v] for d, v in hist.items() if d >= cutoff)
        out["series"][code] = {"series": sid, "label": f"{code}/CAD", "unit": f"CAD per 1 {code}", "history": h}
        s = summarize(h)
        if s:
            s["text_30d"] = describe(code, s, 30)
            s["text_7d"] = describe(code, s, 7)
            out["latest"][code] = s
    return out


# ------------------------------------------------------------------ currency gap (US-priced offers)
def landed_cad(price: float, currency: str, fx: dict, ship: float | None = None, brokerage: float | None = None,
               tax_rate: float = GST) -> dict | None:
    rate = ((fx.get("latest") or {}).get(currency) or {}).get("rate")
    if not rate:
        return None
    goods = price * rate
    ship = DEFAULT_SHIP_CAD if ship is None else ship
    brokerage = DEFAULT_BROKERAGE_CAD if brokerage is None else brokerage
    tax = (goods + ship) * tax_rate
    return {"rate": rate, "goods_cad": round(goods, 2), "ship_cad": round(ship, 2), "brokerage_cad": round(brokerage, 2),
            "tax_cad": round(tax, 2), "landed_cad": round(goods + ship + brokerage + tax, 2), "tax_rate": tax_rate}


def currency_gap(us_offers: list[dict], new_prices: dict, models: dict, listings_by_id: dict, fx: dict) -> list[dict]:
    """us_offers: [{model_key, price, currency ('USD'), condition ('new'|'used'), seller, url, ship_cad?, brokerage_cad?,
    as_of}]. New offers are compared with the cheapest Canadian new price we track; used offers with the cheapest
    Canadian used listing of the same model."""
    out = []
    for o in us_offers:
        mk, cur = o.get("model_key"), (o.get("currency") or "USD").upper()
        if not mk or not o.get("price") or cur == "CAD":
            continue
        ship = o.get("ship_cad")
        rate = ((fx.get("latest") or {}).get(cur) or {}).get("rate")
        if ship is None and o.get("ship_usd") is not None and rate and cur == "USD":
            ship = float(o["ship_usd"]) * rate
        est = landed_cad(float(o["price"]), cur, fx, ship, o.get("brokerage_cad"))
        if not est:
            continue
        cond = (o.get("condition") or "new").lower()
        if cond == "new":
            np = new_prices.get(mk)
            ca_price, ca_where, ca_url = (np["price"], np["dealer"], np["url"]) if np else (None, None, None)
        else:
            m = models.get(mk)
            rows = sorted((listings_by_id[i] for i in (m or {}).get("listing_ids", []) if i in listings_by_id),
                          key=lambda x: x["price_cad"])
            ca_price, ca_where, ca_url = (rows[0]["price_cad"], rows[0]["dealer"], rows[0]["url"]) if rows else (None, None, None)
        if not ca_price:
            continue
        saving = ca_price - est["landed_cad"]
        flagged = saving >= GAP_MIN_CAD and saving >= ca_price * GAP_MIN_PCT
        name = (new_prices.get(mk) or {}).get("name") or (models.get(mk) or {}).get("name") or mk
        out.append({"model_key": mk, "model_name": name, "condition": cond, "seller": o.get("seller"), "url": o.get("url"),
                    "price": o["price"], "currency": cur, "as_of": o.get("as_of"), **est,
                    "ca_price": ca_price, "ca_where": ca_where, "ca_url": ca_url, "saving_cad": round(saving, 2),
                    "saving_pct": round(saving / ca_price, 3), "flagged": flagged,
                    "label": "Estimate: landed cost depends on your province, courier and the seller's shipping."})
    out.sort(key=lambda g: -g["saving_cad"])
    return out


# ------------------------------------------------------------------ rate moved, prices haven't
def rate_moved(new_prices: dict, fx: dict, today: str, currency: str = "USD") -> dict:
    s = (fx.get("latest") or {}).get(currency) or {}
    chg = s.get("chg_30d")
    res = {"currency": currency, "chg_30d": chg, "threshold": RATE_MOVE_MIN, "direction": None, "items": [],
           "tracked_days": 0, "status": ""}
    firsts = [v.get("first_seen") for v in new_prices.values() if v.get("first_seen")]
    tracked = (dt.date.fromisoformat(today) - dt.date.fromisoformat(min(firsts))).days if firsts else 0
    res["tracked_days"] = tracked
    if chg is None:
        res["status"] = "Not enough exchange-rate history yet."
        return res
    if abs(chg) < RATE_MOVE_MIN:
        res["status"] = (f"CAD moved {abs(chg) * 100:.1f}% against the {currency} over 30 days, under the "
                         f"{RATE_MOVE_MIN * 100:.1f}% threshold, so no price flags today.")
        return res
    res["direction"] = "cad_weaker" if chg > 0 else "cad_stronger"
    window = min(30, tracked)
    if tracked < RATE_MOVE_MIN_TRACKED_DAYS:
        res["status"] = (f"CAD moved {abs(chg) * 100:.1f}% against the {currency} over 30 days, but we have only "
                         f"{tracked} days of Canadian new-price history, so we can't yet say which prices haven't moved.")
        return res
    since = (dt.date.fromisoformat(today) - dt.timedelta(days=window)).isoformat()
    for mk, v in new_prices.items():
        h = v.get("history") or []
        if not h or v.get("first_seen", today) > since or v.get("last_seen") != today:
            continue
        if any(d > since for d, _ in h[1:]):
            continue  # price changed inside the window
        res["items"].append({"model_key": mk, "model_name": v["name"], "price": v["price"], "dealer": v["dealer"],
                             "url": v["url"], "unchanged_since": h[-1][0]})
    res["items"].sort(key=lambda x: -x["price"])
    if res["direction"] == "cad_weaker":
        res["status"] = (f"CAD weakened {chg * 100:.1f}% against the {currency} over 30 days. These Canadian new prices "
                         f"haven't changed in {window} days and may rise if dealers reprice imported stock.")
    else:
        res["status"] = (f"CAD strengthened {abs(chg) * 100:.1f}% against the {currency} over 30 days. These Canadian "
                         f"new prices haven't changed in {window} days and may come down if dealers reprice.")
    return res


# ------------------------------------------------------------------ optional eBay US offers (official API)
def ebay_us_offers(model_names: dict[str, str], now: str, max_models: int = 40) -> list[dict]:
    """New-condition, fixed-price eBay.com listings from US sellers that ship to Canada, for a short list of models.
    Runs only when EBAY_CLIENT_ID/EBAY_CLIENT_SECRET exist and EBAY_US_GAP != "0". Returns [] otherwise."""
    if os.environ.get("EBAY_US_GAP") == "0" or not os.environ.get("EBAY_CLIENT_ID") or not os.environ.get("EBAY_CLIENT_SECRET"):
        return []
    from .ebay import SEARCH_URL, _token
    from .normalize import make_listing
    tok = _token(os.environ["EBAY_CLIENT_ID"], os.environ["EBAY_CLIENT_SECRET"])
    headers = {"Authorization": f"Bearer {tok}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
               "X-EBAY-C-ENDUSERCTX": "contextualLocation=country=CA"}
    out = []
    for mk, name in list(model_names.items())[:max_models]:
        q = {"q": name, "filter": "itemLocationCountry:US,deliveryCountry:CA,conditions:{NEW},buyingOptions:{FIXED_PRICE},"
                                  "priceCurrency:USD", "sort": "price", "limit": "50"}
        try:
            r = json.loads(fetch(SEARCH_URL + "?" + urllib.parse.urlencode(q), headers=headers, check_robots=False))
        except Exception:
            continue
        for it in r.get("itemSummaries", []):
            p = (it.get("price") or {})
            if p.get("currency") != "USD":
                continue
            x = make_listing("ebayus", "eBay US", it.get("title", ""), p.get("value"), it.get("itemWebUrl"), fetched_at=now)
            if x.get("model_key") != mk:
                continue
            ship = None
            for so in it.get("shippingOptions") or []:
                c = (so.get("shippingCost") or {})
                if c.get("currency") == "USD" and c.get("value") is not None:
                    ship = float(c["value"])  # converted to CAD by the caller
            out.append({"model_key": mk, "price": float(p["value"]), "currency": "USD", "condition": "new",
                        "seller": "eBay US: " + ((it.get("seller") or {}).get("username") or "seller"),
                        "url": it.get("itemAffiliateWebUrl") or it.get("itemWebUrl"), "ship_usd": ship, "as_of": now})
            break  # results are sorted by price; first exact model match is enough
    return out
