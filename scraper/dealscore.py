"""Deal Score: a transparent 0-100 rating with a plain-English "why", for each used listing that matched a model.
The formula is documented on /about/deal-score/; keep the two in sync.

Components (each 0-100), averaged with the weights below over whichever ones have data:
  history    (0.45) price vs the median of comparable listings (same model, current + last 90 days)
                    50 + 200 x discount, so 25% below the median = 100, at the median = 50, 25% above = 0
  low        (0.10) at or below the lowest price we've recorded for the model in 90 days (needs 5+ observations)
  vs_new     (0.25) used price as a share of the current Canadian new price, against typical used depreciation for
                    the model's age: 50 + 250 x (expected share - actual share). Within 5% of new caps at 20.
  successor  (0.20) only when a newer model replaced it: the gap to the newer model's Canadian new price
Adjustments (points added after the weighted average, only when the price is below the comparable median):
  freshness  announced < 12 months ago +8, < 24 months +4, > 5 years -4 (new models rarely discount)
Sale cycles: counts the Black Friday / Boxing Day / Prime Day / rebate windows a model has been on sale through and,
once we have our own price history across an event, compares today's price with the event low.
Models without curated metadata (data/model-meta.json) fall back to history and new-price comparisons and say so.
"""
from __future__ import annotations

import datetime as dt
import statistics

WEIGHTS = {"history": 0.45, "low": 0.10, "vs_new": 0.25, "successor": 0.20}
# typical used price as a share of the current new price, by model age (rough rule of thumb for bodies & lenses
# in good condition at Canadian dealers; tuned from our own data over time)
DEPRECIATION = [(12, 0.85), (24, 0.78), (48, 0.70), (10_000, 0.60)]
DEPRECIATION_UNKNOWN_AGE = 0.75
MIN_LOW_OBS = 5


def clamp(x: float, lo: float = 0, hi: float = 100) -> float:
    return max(lo, min(hi, x))


def months_between(a: str, b: str) -> float:
    da, db = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    return (db - da).days / 30.44


def expected_share(age_months: float | None) -> float:
    if age_months is None:
        return DEPRECIATION_UNKNOWN_AGE
    return next(s for m, s in DEPRECIATION if age_months < m)


# ------------------------------------------------------------------ sale calendar
def black_friday(year: int) -> dt.date:
    d = dt.date(year, 11, 1)
    first_thu = d + dt.timedelta(days=(3 - d.weekday()) % 7)
    return first_thu + dt.timedelta(days=22)  # 4th Thursday + 1


def sale_events(start: str, end: str) -> list[dict]:
    """Major sale windows between two ISO dates. Black Friday/Cyber Monday and Boxing Week are fixed by the calendar;
    Prime Day and manufacturer rebate windows move every year, so their windows are approximate."""
    s, e = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    out = []
    for y in range(s.year, e.year + 2):
        bf = black_friday(y)
        for name, a, b, approx in [
            ("Spring rebates", dt.date(y, 4, 1), dt.date(y, 5, 31), True),
            ("Prime Day", dt.date(y, 7, 8), dt.date(y, 7, 17), True),
            ("Summer rebates", dt.date(y, 7, 1), dt.date(y, 8, 31), True),
            ("Black Friday / Cyber Monday", bf, bf + dt.timedelta(days=3), False),
            ("Boxing Week", dt.date(y, 12, 26), dt.date(y, 12, 31), False),
        ]:
            out.append({"name": name, "start": a.isoformat(), "end": b.isoformat(), "approx": approx})
    return sorted(out, key=lambda x: x["start"])


def sale_cycles(announced: str | None, today: str) -> dict:
    evs = sale_events(announced or today, today)
    survived = [ev for ev in evs if announced and ev["start"] > announced and ev["end"] < today]
    upcoming = next((ev for ev in evs if ev["start"] >= today), None)
    bfs = sum(1 for ev in survived if ev["name"].startswith("Black Friday"))
    return {"survived": len(survived), "black_fridays": bfs, "next": upcoming}


def event_low(history: list[list], first_seen: str, events: list[dict], today: str) -> tuple[float, str] | None:
    """Lowest price we recorded during a past sale window (needs our history to cover the window)."""
    best = None
    for ev in events:
        if first_seen > ev["start"] or ev["end"] >= today:
            continue
        in_effect = [q for d, q in history if d <= ev["start"]][-1:]
        during = [q for d, q in history if ev["start"] <= d <= ev["end"]]
        vals = in_effect + during
        price = min(vals) if vals else None
        if price is not None and (best is None or price < best[0]):
            best = (price, ev["name"] + " " + ev["start"][:4])
    return best


# ------------------------------------------------------------------ scoring
def score_listing(x: dict, comps: list[float], low90: float | None, n_obs90: int, new_prices: dict, meta: dict,
                  today: str) -> dict | None:
    p, mk = x["price_cad"], x.get("model_key")
    if not mk or not p:
        return None
    parts, why = {}, []
    m = (meta or {}).get(mk)
    age = months_between(m["announced"], today) if m and m.get("announced") else None
    disc = None
    if len(comps) >= 3:
        med = statistics.median(comps)
        disc = 1 - p / med
        parts["history"] = clamp(50 + 200 * disc)
        if abs(disc) < 0.03:
            why.append(f"about the typical price of {len(comps)} comparable listings")
        else:
            why.append(f"{abs(disc) * 100:.0f}% {'below' if disc > 0 else 'above'} the median of {len(comps)} comparable listings")
    if low90 is not None and n_obs90 >= MIN_LOW_OBS and p <= low90:
        parts["low"] = 90
        why.append("the lowest price we've recorded for this model in 90 days")
    # bundles ("with 24-70", "kit") and titles whose version marker disagrees with the model key ("Z6 MK2" grouped as
    # Z6) are not compared with a body-only new price or a successor: the match is probably wrong
    from .newprices import BUNDLE_RX, _version_ok
    comparable = not (x.get("category") == "camera" and BUNDLE_RX.search(x.get("title", ""))) \
        and _version_ok(x.get("title", ""), mk, x.get("category") or "")
    if not comparable:
        m, age = None, None
    np = new_prices.get(mk) if comparable else None
    if np and np.get("price"):
        share = p / np["price"]
        if 0.25 <= share <= 1.3:  # outside this range the "same model" match is probably wrong (kit, version)
            exp = expected_share(age)
            v = clamp(50 + 250 * (exp - share))
            if share >= 1:
                v = 0
                why.append(f"priced at or above the new price ({np['dealer']}, ${np['price']:,.0f})")
            elif share >= 0.95:
                v = min(v, 20)
                why.append(f"only {(1 - share) * 100:.0f}% under the new price ({np['dealer']}, ${np['price']:,.0f}); new comes with a full warranty")
            else:
                why.append(f"{share * 100:.0f}% of the new price (${np['price']:,.0f}); used ones this age typically sell around {exp * 100:.0f}%")
            parts["vs_new"] = v
    if m and m.get("successor"):
        sn = new_prices.get(m["successor"])
        sname = ((meta or {}).get(m["successor"]) or {}).get("name") or (sn or {}).get("name") or "newer model"
        if sn and sn.get("price") and 0.2 <= p / sn["price"] <= 1.5:
            r = p / sn["price"]
            more = sn["price"] / p - 1
            if more <= 0.15:
                parts["successor"] = 15
                why.append(f"better value may be the newer {sname}: it costs only {max(0, more) * 100:.0f}% more new")
            elif r <= 0.55:
                parts["successor"] = 85
                why.append(f"great value: previous generation at {r * 100:.0f}% of the newer {sname}'s price")
            else:
                parts["successor"] = clamp(50 + (0.75 - r) * 150)
                why.append(f"{r * 100:.0f}% of the price of its replacement, the {sname}")
    if not parts:
        return None
    w = sum(WEIGHTS[k] for k in parts)
    score = sum(parts[k] * WEIGHTS[k] for k in parts) / w
    adj = 0
    if age is not None and disc is not None and disc > 0:
        if age < 12:
            adj = 8
            why.append("a discount on a model announced in the last year is unusual")
        elif age < 24:
            adj = 4
        elif age > 60:
            adj = -4
    score = round(clamp(score + adj))
    cyc = sale_cycles(m.get("announced") if m else None, today) if m else None
    if cyc and m.get("announced"):
        why.append(f"announced {m['announced'][:7]}: on sale through {cyc['black_fridays']} Black Fridays so far")
    basis = "full" if m else "history only (no model metadata yet)"
    if not m and comparable:
        why.append("no release-date or successor data for this model yet, so the score uses price history only")
    elif not comparable:
        basis = "history only (bundle or version mismatch)"
        why.append("looks like a kit or a different version, so it is only compared with similar listings")
    return {"score": score, "why": why, "parts": {k: round(v) for k, v in parts.items()}, "adj": adj, "basis": basis}


def label(score: int) -> str:
    return "Great" if score >= 80 else "Good" if score >= 65 else "Fair" if score >= 45 else "Weak"


def score_new_price(mk: str, new_prices: dict, meta: dict, today: str) -> dict | None:
    """Model-level note on the current Canadian NEW price: sale-cycle context and 'wait for Black Friday' hints."""
    np, m = new_prices.get(mk), (meta or {}).get(mk)
    if not np:
        return None
    cyc = sale_cycles(m.get("announced") if m else None, today)
    notes = []
    low = event_low(np.get("history") or [], np.get("first_seen", today), sale_events(np.get("first_seen", today), today), today)
    if low:
        if np["price"] <= low[0]:
            notes.append(f"at or below its {low[1]} price (${low[0]:,.0f})")
        else:
            notes.append(f"above its {low[1]} price (${low[0]:,.0f}); consider waiting for the next sale")
    else:
        notes.append("we haven't tracked this model's new price through a sale event yet")
    nxt = cyc.get("next")
    if nxt:
        days = (dt.date.fromisoformat(nxt["start"]) - dt.date.fromisoformat(today)).days
        if nxt["name"].startswith("Black Friday") and days <= 45 and (not m or cyc["black_fridays"] >= 1):
            notes.append(f"Black Friday starts {nxt['start']} ({days} days): models that have been out a year or more often see sale prices then")
    if m and m.get("announced"):
        notes.append(f"announced {m['announced']}; on sale through {cyc['black_fridays']} Black Fridays and {cyc['survived']} sale windows in all")
    return {"price": np["price"], "dealer": np["dealer"], "url": np["url"], "notes": notes, "cycles": cyc}
