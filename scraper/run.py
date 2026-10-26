"""Daily pipeline: scrape -> normalize -> history/state -> models -> changes -> deals -> rebates.

Model pages are not only today's listings. data/model-seen.json remembers each model we have
actually matched, with the last day and price, so the site can keep that page for RETAIN_DAYS
after the listings disappear. Past that, the page is dropped and (once Pages' asset cache
expires) returns 404. Cloudflare Pages _redirects cannot answer 404 (status 404 is an
unsupported rewrite), so no redirect is written.

Usage: python -m scraper.run [dealer ...]   (default: all dealers + eBay if keys present)
All outputs land in data/. Dates are America/Edmonton calendar days.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import statistics
import sys
import time
import traceback
from pathlib import Path
from zoneinfo import ZoneInfo

from . import currency, dealscore, newprices
from .dealers import ADAPTERS, DEALERS
from .ebay import ebay
from .rebates import rebates

DATA = Path(os.environ.get("USEDGLASS_DATA", Path(__file__).resolve().parent.parent / "data"))
TZ = ZoneInfo("America/Edmonton")
DEAL_MIN_DISCOUNT = 0.20
DEAL_MIN_COMPS = 3
DROP_MIN = 0.10
DEAL_MAX_DISCOUNT = 0.70
HISTORY_DAYS = 120
RETAIN_DAYS = 90            # keep a model page this many days after its last matched listing
DROP_ALERT_RATIO = 0.4      # warn when a dealer returns <40% of yesterday's listings (partial layout break)
DROP_ALERT_MIN_PREV = 25


def load(path: Path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save(path: Path, obj, compact: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if compact else json.dumps(obj, ensure_ascii=False, indent=1)
    path.write_text(txt + "\n")


def floor_cheap_cameras(listings: list[dict], state: dict) -> None:
    """A "camera" under 20% of the median of the same model's other body-only listings is an accessory the title
    matcher mistook for the body (a case, a grip): keep it searchable, just off the model page."""
    by_mk: dict[str, list[dict]] = {}
    for x in listings:
        if x.get("model_key") and x.get("category") == "camera" and x.get("price_cad"):
            by_mk.setdefault(x["model_key"], []).append(x)
    for xs in by_mk.values():
        for x in xs:
            others = [o["price_cad"] for o in xs if o is not x and not o.get("bundle")]
            if others and x["price_cad"] < 0.2 * statistics.median(others):
                x["model_key"], x["model_name"], x["category"] = None, None, "accessory"
                if x["id"] in state:
                    state[x["id"]]["mk"] = None


def price_stats(xs: list[dict]) -> dict:
    """count, min_price (bundles included: a kit is sometimes the cheapest way to get the body) and median_price
    (body-only listings when there are any, since camera + lens bundles skew a body's typical price)."""
    prices = sorted(x["price_cad"] for x in xs)
    solo = sorted(x["price_cad"] for x in xs if not x.get("bundle")) or prices
    return {"count": len(prices), "min_price": prices[0], "median_price": round(statistics.median(solo), 2)}


def iso_minus(day: str, days: int) -> str:
    return (dt.date.fromisoformat(day) - dt.timedelta(days=days)).isoformat()


def model_key_ok(key) -> bool:
    """Model keys become URL paths (/model/<key>/). Reject anything that is not a plain slug."""
    if not isinstance(key, str) or not 1 <= len(key) <= 120 or key != key.lower() or not key[0].isalnum():
        return False
    return all(c.isalnum() or c in "-_" for c in key)


def _iso_date(value) -> str | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _price(value):
    """A real positive price. Booleans are ints in Python and are not prices."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not value > 0:
        return None
    return round(float(value), 2)


def state_model_stats(state: dict, today: str, retain_days: int = RETAIN_DAYS) -> dict:
    """Per model key still tagged on a listing seen within retain_days: last day, the prices that day, and the
    last price of each such listing (the same 90-day inputs models.json uses for median_90d)."""
    since = iso_minus(today, retain_days)
    out: dict[str, dict] = {}
    for s in state.values():
        mk = s.get("mk")
        points = s.get("p") or []
        if not model_key_ok(mk) or not points:
            continue
        ls = _iso_date(s.get("ls") or points[-1][0])
        price = _price(points[-1][1])
        if not ls or ls < since or price is None:
            continue
        a = out.setdefault(mk, {"last_seen": "", "last_prices": [], "obs": []})
        a["obs"].append(price)
        if ls > a["last_seen"]:
            a["last_seen"] = ls
            a["last_prices"] = [price]
        elif ls == a["last_seen"]:
            a["last_prices"].append(price)
    return out


def _seen_row(name: str, category, brand, mount) -> dict:
    return {
        "name": name,
        "category": category or None,
        "brand": brand or None,
        "mount": mount or None,
        "last_seen": None,
        "last_price": None,
        "median_90d": None,
        "observations_90d": 0,
        "median_90d_as_of": None,
    }


def update_model_seen(prev: dict, models: dict, state: dict, today: str, retain_days: int = RETAIN_DAYS,
                      new_prices: dict | None = None) -> dict:
    """Registry of models we have actually matched.

    Identity (name, category, brand, mount) is copied from a current listing group or from a previous row.
    last_seen / last_price / median_90d come from today's models or from listing state. A row with no name,
    or last seen more than retain_days ago, is dropped. Nothing is invented: a model key that appears only
    in state, with no previous name, is skipped.
    """
    if not _iso_date(today):
        raise ValueError(f"bad today: {today!r}")
    cutoff = iso_minus(today, retain_days)
    stats = state_model_stats(state, today, retain_days)
    reg: dict[str, dict] = {}
    for mk, e in (prev or {}).items():
        if not model_key_ok(mk) or not isinstance(e, dict):
            continue
        name = e.get("name")
        last = _iso_date(e.get("last_seen"))
        if not isinstance(name, str) or not name.strip() or not last:
            continue
        if last < cutoff and mk not in models:
            continue
        row = _seen_row(name.strip(), e.get("category"), e.get("brand"), e.get("mount"))
        row["last_seen"] = last
        row["last_price"] = _price(e.get("last_price"))
        row["median_90d"] = _price(e.get("median_90d"))
        obs = e.get("observations_90d")
        row["observations_90d"] = int(obs) if isinstance(obs, int) and not isinstance(obs, bool) and obs > 0 else 0
        row["median_90d_as_of"] = _iso_date(e.get("median_90d_as_of")) or last
        reg[mk] = row
    for mk, m in models.items():
        if not model_key_ok(mk) or not isinstance(m, dict):
            continue
        name = m.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        row = reg.get(mk) or _seen_row(name.strip(), m.get("category"), m.get("brand"), m.get("mount"))
        row["name"] = name.strip()
        row["category"] = m.get("category") or None
        row["brand"] = m.get("brand") or None
        row["mount"] = m.get("mount") or None
        row["last_seen"] = today
        row["last_price"] = _price(m.get("min_price"))
        row["median_90d"] = _price(m.get("median_90d"))
        obs = m.get("observations_90d")
        row["observations_90d"] = int(obs) if isinstance(obs, int) and not isinstance(obs, bool) and obs > 0 else 0
        row["median_90d_as_of"] = today
        reg[mk] = row
    for mk, a in stats.items():
        if mk in models or mk not in reg:
            continue
        row = reg[mk]
        if a["last_seen"] >= (row.get("last_seen") or ""):
            row["last_seen"] = a["last_seen"]
            if a["last_prices"]:
                row["last_price"] = min(a["last_prices"])
        if a["obs"]:
            row["median_90d"] = round(statistics.median(a["obs"]), 2)
            row["observations_90d"] = len(a["obs"])
            row["median_90d_as_of"] = today
    if new_prices is not None:
        for mk, row in reg.items():
            np = new_prices.get(mk) or {}
            price, url = _price(np.get("price")), np.get("url")
            if price and isinstance(url, str) and url.startswith("http"):
                row["new_price"] = price
                row["new_price_url"] = url
                row["new_price_dealer"] = np.get("dealer") or None
    return {k: reg[k] for k in sorted(reg) if reg[k].get("last_seen") and reg[k]["last_seen"] >= cutoff and reg[k].get("name")}


def main(argv: list[str]) -> int:
    now_dt = dt.datetime.now(dt.timezone.utc)
    now = now_dt.isoformat(timespec="seconds")
    today = now_dt.astimezone(TZ).date().isoformat()
    picks = [k for k in argv if k != "newprices"] or list(ADAPTERS) + ["ebay"]
    prev_listings = {x["id"]: x for x in load(DATA / "listings.json", [])}
    prev_meta = load(DATA / "meta.json", {})
    state = load(DATA / "state.json", {})
    meta = {"run_at": now, "date": today, "dealers": {}, "errors": {}}

    listings: list[dict] = []
    for k in picks:
        t0 = time.time()
        try:
            rows = ebay(now) if k == "ebay" else ADAPTERS[k](now)
            if k == "ebay" and not rows:
                meta["dealers"][k] = {"count": 0, "status": "skipped (no API keys)" if not os.environ.get("EBAY_CLIENT_ID") else "empty"}
                continue
            if not rows:
                raise RuntimeError("0 listings parsed (layout change?)")
            listings += rows
            meta["dealers"][k] = {"count": len(rows), "status": "ok", "seconds": round(time.time() - t0, 1)}
            prev = (prev_meta.get("dealers") or {}).get(k) or {}
            if prev.get("status") == "ok" and prev.get("count", 0) >= DROP_ALERT_MIN_PREV \
                    and len(rows) < prev["count"] * DROP_ALERT_RATIO:
                meta["dealers"][k]["warning"] = f"listing count fell from {prev['count']} to {len(rows)}"
        except Exception as e:
            traceback.print_exc()
            stale = [x for x in prev_listings.values() if x["dealer_id"] == k]
            for x in stale:
                x["stale"] = True
            listings += stale
            meta["errors"][k] = f"{type(e).__name__}: {e}"
            meta["dealers"][k] = {"count": len(stale), "status": "error - kept previous listings"}
        print(k, meta["dealers"][k], flush=True)

    # de-dup ids, drop junk prices
    uniq = {}
    for x in listings:
        if x.get("price_cad") and x["price_cad"] >= 10:
            uniq[x["id"]] = x
    listings = list(uniq.values())

    # ---- state + history
    hist = {}
    new_ids, dropped = [], []
    for x in listings:
        s = state.get(x["id"])
        p = x["price_cad"]
        if s is None:
            s = {"fs": today, "p": [[today, p]], "mk": x.get("model_key")}
            if x["id"] not in prev_listings:
                new_ids.append(x["id"])
        else:
            last = s["p"][-1][1]
            if p != last:
                s["p"].append([today, p])
                if p < last * (1 - 0.001):
                    dropped.append({"id": x["id"], "old": last, "new": p, "pct": round(1 - p / last, 3)})
        s["ls"] = today
        s["mk"] = x.get("model_key")
        state[x["id"]] = s
        x["first_seen"] = s["fs"]
        x["prev_price"] = s["p"][-2][1] if len(s["p"]) > 1 else None
        x["lowest_seen"] = min(v for _, v in s["p"])
        hist[x["id"]] = p
    # prune state entries unseen for > HISTORY_DAYS
    cutoff = (dt.date.fromisoformat(today) - dt.timedelta(days=HISTORY_DAYS)).isoformat()
    state = {k: v for k, v in state.items() if v.get("ls", today) >= cutoff}
    save(DATA / "history" / f"{today}.json", {"date": today, "run_at": now, "prices": hist}, compact=True)

    # ---- models
    # Price sanity: a "camera" listed under 20% of the median of the same model's other listings is an accessory
    # the title matcher mistook for the body (a case, a grip). Keep it searchable, just off the model page.
    # Lenses are not floored: cheap third-party or worn copies are real and are often the best deals.
    floor_cheap_cameras(listings, state)
    current_ids = {x["id"] for x in listings}
    models: dict[str, dict] = {}
    for x in listings:
        mk = x.get("model_key")
        if not mk:
            continue
        m = models.setdefault(mk, {"key": mk, "name": x["model_name"], "category": x["category"], "brand": x["brand"],
                                   "mount": x["mount"], "listing_ids": []})
        m["listing_ids"].append(x["id"])
        if not m["mount"] and x["mount"]:
            m["mount"] = x["mount"]
    hist_by_model: dict[str, list[float]] = {}
    for lid, s in state.items():
        if s.get("mk") and s.get("ls", "") >= (dt.date.fromisoformat(today) - dt.timedelta(days=90)).isoformat():
            hist_by_model.setdefault(s["mk"], []).append(s["p"][-1][1])
    by_id = {x["id"]: x for x in listings}
    for mk, m in models.items():
        # Camera + lens bundles skew a body's typical price: the median uses body-only listings when there are any.
        # The minimum keeps bundles, since a kit is sometimes the cheapest way to get the body.
        m.update(price_stats([by_id[i] for i in m["listing_ids"]]))
        hp = hist_by_model.get(mk, [])
        m["median_90d"] = round(statistics.median(hp), 2) if hp else None
        m["observations_90d"] = len(hp)
        m["dealers"] = sorted({by_id[i]["dealer_id"] for i in m["listing_ids"]})
    # ---- Canadian new-gear reference prices (The Camera Store public catalogue), FX, Deal Score
    feeds = {}
    new_prices = load(DATA / "new-prices.json", {})
    if not argv or "newprices" in argv:
        t0 = time.time()
        try:
            tcs_urls = {x["url"] for x in listings if x["dealer_id"] == "thecamerastore"}
            rows = newprices.fetch_new(now, tcs_urls)
            if not rows:
                raise RuntimeError("0 new-price rows parsed")
            new_prices = newprices.update(new_prices, rows, today)
            feeds["newprices"] = {"count": len(new_prices), "status": "ok", "seconds": round(time.time() - t0, 1)}
        except Exception as e:
            traceback.print_exc()
            feeds["newprices"] = {"count": len(new_prices), "status": f"error - kept previous ({type(e).__name__}: {e})"}
        save(DATA / "new-prices.json", new_prices, compact=True)
    fx = currency.fx_update(load(DATA / "fx.json", {}), today, now)
    feeds["fx"] = {"status": "ok" if not fx.get("error") else "error - kept previous: " + fx["error"],
                   "latest": (fx["latest"].get("USD") or {}).get("date")}
    save(DATA / "fx.json", fx)
    model_meta = load(DATA / "model-meta.json", {}).get("models", {})

    by_id_all = {x["id"]: x for x in listings}
    obs90 = {}
    since90 = (dt.date.fromisoformat(today) - dt.timedelta(days=90)).isoformat()
    for lid, s_ in state.items():
        if s_.get("mk") and s_.get("ls", "") >= since90:
            obs90.setdefault(s_["mk"], []).extend(v for d, v in s_["p"] if d >= since90 or v == s_["p"][-1][1])
    for x in listings:
        mk = x.get("model_key")
        if not mk or x.get("condition") == "As Is":
            continue
        comps = [by_id_all[i]["price_cad"] for i in models[mk]["listing_ids"]
                 if i != x["id"] and by_id_all[i].get("condition") != "As Is"]
        comps += [s_["p"][-1][1] for lid, s_ in state.items() if s_.get("mk") == mk and lid not in by_id_all
                  and s_.get("ls", "") >= since90]
        o = obs90.get(mk, [])
        sc = dealscore.score_listing(x, comps, min(o) if o else None, len(o), new_prices, model_meta, today)
        if sc:
            x["deal_score"], x["score_why"], x["score_basis"] = sc["score"], sc["why"], sc["basis"]
            x["score_parts"] = sc["parts"]
    for mk, m in models.items():
        scored = [by_id_all[i] for i in m["listing_ids"] if by_id_all[i].get("deal_score") is not None]
        if scored:
            best = max(scored, key=lambda y: y["deal_score"])
            m["best_score"], m["best_score_id"] = best["deal_score"], best["id"]
        np_ = new_prices.get(mk)
        if np_:
            m["new_price"], m["new_price_url"], m["new_price_dealer"] = np_["price"], np_["url"], np_["dealer"]
            note = dealscore.score_new_price(mk, new_prices, model_meta, today)
            if note:
                m["new_price_notes"] = note["notes"]
        if mk in model_meta:
            mm = model_meta[mk]
            m["meta"] = {k: mm.get(k) for k in ("announced", "successor", "predecessor", "msrp_usd", "sources")}
            if mm.get("successor"):
                m["meta"]["successor_name"] = (model_meta.get(mm["successor"]) or {}).get("name")
    save(DATA / "models.json", models, compact=True)
    # Remember every model we matched so a page can outlive a gap in listings. Rows older than RETAIN_DAYS
    # are dropped here; the site also refuses to build a page past that cutoff. No name is guessed from the key.
    seen_prev = load(DATA / "model-seen.json", {})
    seen_models_prev = seen_prev.get("models") if isinstance(seen_prev, dict) else {}
    seen_models = update_model_seen(
        seen_models_prev if isinstance(seen_models_prev, dict) else {},
        models, state, today, new_prices=new_prices,
    )
    save(DATA / "model-seen.json", {
        "_about": "Models actually matched to a dealer listing, with the last day and price we saw. "
                  "The site keeps an indexable /model/<key>/ page for retain_days after last_seen, then drops it. "
                  "Written by scraper/run.py. Prices are copied from listings or listing state, never estimated.",
        "retain_days": RETAIN_DAYS,
        "updated": today,
        "models": seen_models,
    }, compact=True)

    # ---- deals
    deals = []
    dropped_by_id = {d["id"]: d for d in dropped}
    for x in listings:
        if x.get("condition") == "As Is" or x.get("stale"):
            continue
        p = x["price_cad"]
        reasons, score, comp_median, ncomp = [], 0.0, None, 0
        mk = x.get("model_key")
        if mk:
            comps = [by_id[i]["price_cad"] for i in models[mk]["listing_ids"]
                     if i != x["id"] and by_id[i].get("condition") != "As Is"]
            comps += [v for lid, s in state.items() if s.get("mk") == mk and lid not in current_ids
                      for v in [s["p"][-1][1]]]
            ncomp = len(comps)
            if ncomp >= DEAL_MIN_COMPS:
                comp_median = statistics.median(comps)
                disc = 1 - p / comp_median
                if DEAL_MIN_DISCOUNT <= disc <= DEAL_MAX_DISCOUNT:  # >70% off is almost always a mismatch
                    reasons.append(f"{round(disc * 100)}% below the median of {ncomp} comparable listings")
                    score += disc * 100 + min(ncomp, 10)
        d = dropped_by_id.get(x["id"])
        if d and d["pct"] >= DROP_MIN:
            reasons.append(f"price dropped {round(d['pct'] * 100)}% (was ${d['old']:,.0f})")
            score += d["pct"] * 60
        if not reasons:
            continue
        if x["id"] in new_ids:
            score += 8
        deals.append({"type": "listing", "id": x["id"], "title": x["title"], "dealer": x["dealer"], "url": x["url"],
                      "price_cad": p, "comp_median": round(comp_median, 2) if comp_median else None, "comps": ncomp,
                      "model_key": mk, "model_name": x.get("model_name"), "condition": x.get("condition"),
                      "reasons": reasons, "score": round(score, 1), "is_new": x["id"] in new_ids,
                      "deal_score": x.get("deal_score"), "score_why": x.get("score_why"),
                      "score_basis": x.get("score_basis"), "fetched_at": x["fetched_at"]})
    # sorted by Deal Score (0-100, see scraper/dealscore.py); the older flag score breaks ties / covers unscored
    deals.sort(key=lambda d: (-(d["deal_score"] if d.get("deal_score") is not None else -1), -d["score"]))

    # ---- rebates (new rebate pages become deals too)
    prev_reb = load(DATA / "rebates.json", {"items": []})
    try:
        reb = rebates(now)
    except Exception as e:
        reb = dict(prev_reb, errors=[{"error": f"{type(e).__name__}: {e}"}])
    prev_urls = {r["url"] for r in prev_reb.get("items", [])}
    for r in reb.get("items", []):
        r["first_seen"] = next((p.get("first_seen") for p in prev_reb.get("items", []) if p["url"] == r["url"]), today) or today
        if r["url"] not in prev_urls and prev_reb.get("items"):
            deals.insert(0, {"type": "rebate", "id": "rebate-" + r["url"], "title": f"New {r['brand']} rebate: {r['title']}",
                             "url": r["url"], "dealer": r["brand"], "price_cad": None,
                             "reasons": [f"up to ${r['max_amount_cad']:,}" if r.get("max_amount_cad") else "new manufacturer offer"],
                             "score": 999, "is_new": True, "fetched_at": now})
    save(DATA / "rebates.json", reb)

    # ---- currency signals (Bank of Canada rates); US offers come from data/us-offers.json + eBay US API if keys exist
    us = [o for o in load(DATA / "us-offers.json", {}).get("items", [])
          if (o.get("as_of") or today)[:10] >= (dt.date.fromisoformat(today) - dt.timedelta(days=7)).isoformat()]
    n_manual = len(us)
    try:
        wanted = {k: (model_meta.get(k) or {}).get("name") or v["name"] for k, v in new_prices.items()
                  if k in model_meta or v.get("category") == "camera"}
        ebay_us = currency.ebay_us_offers(dict(sorted(wanted.items(), key=lambda kv: kv[0] not in model_meta)), now)
        feeds["ebay_us"] = {"count": len(ebay_us), "status": "ok" if os.environ.get("EBAY_CLIENT_ID") else "skipped (no API keys)"}
        us += ebay_us
    except Exception as e:
        feeds["ebay_us"] = {"count": 0, "status": f"error: {type(e).__name__}: {e}"}
    gaps = currency.currency_gap(us, new_prices, models, by_id, fx)
    moved = currency.rate_moved(new_prices, fx, today, "USD")
    cur_out = {"date": today, "generated_at": now, "fx_latest": fx.get("latest"), "fx_source": fx.get("source"),
               "fx_source_url": fx.get("source_url"), "fx_error": fx.get("error"),
               "us_offer_sources": {"manual_or_feed": n_manual,
                                    "ebay_us": feeds["ebay_us"]},
               "gap_rules": {"min_pct": currency.GAP_MIN_PCT, "min_cad": currency.GAP_MIN_CAD,
                             "default_ship_cad": currency.DEFAULT_SHIP_CAD, "default_brokerage_cad": currency.DEFAULT_BROKERAGE_CAD,
                             "tax_rate": currency.GST, "tax_note": currency.TAX_NOTE, "duty_note": currency.DUTY_NOTE},
               "gaps": gaps[:100], "rate_moved": moved, "new_price_models": len(new_prices)}
    save(DATA / "currency.json", cur_out)
    for g in reversed([g for g in gaps if g["flagged"]][:10]):
        deals.insert(0, {"type": "currency_gap", "id": f"gap-{g['model_key']}-{g['seller']}", "title": f"{g['model_name']} from {g['seller']} (US)",
                      "dealer": g["seller"], "url": g["url"], "price_cad": g["landed_cad"], "model_key": g["model_key"],
                      "model_name": g["model_name"], "reasons": [f"estimated landed cost ${g['landed_cad']:,.0f} vs ${g['ca_price']:,.0f} at {g['ca_where']} (estimate: shipping, brokerage and GST included; HST provinces pay more)"],
                      "score": 0, "deal_score": None, "is_new": False, "fetched_at": g.get("as_of") or now})

    # ---- deal of the day (prefer something new/dropped today, avoid repeats in last 14 days)
    dotd_hist = load(DATA / "deal-of-the-day.json", [])
    recent = {h["id"] for h in dotd_hist[-14:]}
    fresh = [d for d in deals if d["id"] not in recent]
    pick = next((d for d in fresh if d.get("is_new") or d["id"] in dropped_by_id), fresh[0] if fresh else None)
    if pick and not (dotd_hist and dotd_hist[-1].get("date") == today):
        dotd_hist.append(dict(pick, date=today))
    elif pick and dotd_hist and dotd_hist[-1].get("date") == today:
        dotd_hist[-1] = dict(pick, date=today)
    save(DATA / "deal-of-the-day.json", dotd_hist[-120:])
    save(DATA / "deals.json", {"date": today, "generated_at": now, "deal_of_the_day": pick, "deals": deals[:100],
                               "rules": {"min_discount": DEAL_MIN_DISCOUNT, "min_comps": DEAL_MIN_COMPS, "min_drop": DROP_MIN}})

    # ---- changes + listings + meta
    removed = [i for i in prev_listings if i not in current_ids]
    fx_usd = (fx.get("latest") or {}).get("USD") or {}
    save(DATA / "newsletter.json", {
        "date": today, "note": "Data hook for the weekly Kit broadcast; regenerated daily.",
        "fx": {c: {k: v.get(k) for k in ("date", "rate", "chg_7d", "chg_30d", "text_30d")} for c, v in (fx.get("latest") or {}).items()},
        "fx_headline": fx_usd.get("text_30d"), "rate_moved": {k: moved[k] for k in ("status", "direction")} | {"items": moved["items"][:5]},
        "currency_gaps": [g for g in gaps if g["flagged"]][:5],
        "top_scored_deals": [{k: d.get(k) for k in ("title", "dealer", "url", "price_cad", "deal_score", "score_why", "model_name")}
                             for d in deals if d.get("deal_score") is not None][:10],
    })
    save(DATA / "changes.json", {"date": today, "new_today": new_ids, "price_dropped": dropped, "removed": len(removed)})
    listings.sort(key=lambda x: (x["dealer_id"], x["title"]))
    save(DATA / "listings.json", listings, compact=True)
    save(DATA / "state.json", state, compact=True)
    meta.update({"total": len(listings), "models": len(models), "new_today": len(new_ids),
                 "price_dropped": len(dropped), "deals": len(deals), "dealer_info": DEALERS, "feeds": feeds})
    save(DATA / "meta.json", meta)
    print(json.dumps({k: meta[k] for k in ["total", "models", "new_today", "price_dropped", "deals"]}))
    ok = [k for k, v in meta["dealers"].items() if v["status"] == "ok"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
