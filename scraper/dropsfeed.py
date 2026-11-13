"""Weekly "biggest drop" rollup: data/biggest-drops.json, served at /feeds/biggest-drops.json and .xml.

/drops/ and data/changes.json only cover the change since the previous daily check. This looks back seven
days, using the per-listing price points in data/state.json, and keeps the largest markdowns that are still
for sale today. scraper/run.py calls build() once listings and state are final and saves the result.
"""
from __future__ import annotations

import datetime as dt

WINDOW_DAYS = 7
MIN_PCT = 0.05     # keep a drop of at least 5% ...
MIN_SAVED = 50.0   # ... or at least $50 CAD, so a big-ticket markdown counts when the percent is small
MAX_PCT = 0.70     # same cut-off as deals (DEAL_MAX_DISCOUNT): a bigger move is almost always a mismatch
MAX_ITEMS = 25


def _num(v) -> float | int:
    """9.0 -> 9, 149.949999 -> 149.95, so the feed never shows float noise."""
    v = round(float(v), 2)
    return int(v) if v == int(v) else v


def week_drop(points: list, week_start: str, today: str) -> tuple[float, float, str] | None:
    """(old_price, new_price, drop_date) for one listing's price points, or None when it has no price change
    inside the window.

    old_price is the last price on or before week_start. A listing first seen after week_start has no such
    price, so its first price is used. new_price is the latest price up to today, and drop_date is the day
    that price appeared.
    """
    pts = sorted((d, p) for d, p in points if isinstance(d, str) and d <= today and isinstance(p, (int, float)) and p > 0)
    if len(pts) < 2:
        return None
    before = [x for x in pts if x[0] <= week_start]
    old = before[-1] if before else pts[0]
    new = pts[-1]
    if new[0] <= week_start or new[0] == old[0]:
        return None
    return old[1], new[1], new[0]


def build(listings: list[dict], state: dict, today: str, generated_at: str | None = None,
          max_pct: float = MAX_PCT, limit: int = MAX_ITEMS) -> dict:
    """The feed document. Always valid, with an empty items list when nothing dropped."""
    week_start = (dt.date.fromisoformat(today) - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    items = []
    for x in listings:
        if x.get("stale") or x.get("condition") == "As Is":
            continue
        found = week_drop((state.get(x.get("id")) or {}).get("p") or [], week_start, today)
        if not found:
            continue
        old, new, drop_date = found
        if new >= old:
            continue
        pct, saved = 1 - new / old, old - new
        if pct > max_pct or (pct < MIN_PCT and saved < MIN_SAVED):
            continue
        mk = x.get("model_key")
        items.append({
            "id": x["id"], "title": x.get("title"), "dealer": x.get("dealer"), "url": x.get("url"),
            "model_key": mk, "model_name": x.get("model_name"), "category": x.get("category"),
            "old_price": _num(old), "new_price": _num(new), "pct": round(pct, 3), "saved_cad": _num(saved),
            "drop_date": drop_date, "model_path": f"/model/{mk}/" if mk else None,
        })
    items.sort(key=lambda i: (-i["pct"], -i["saved_cad"], i["id"]))
    items = items[:limit]
    return {"week_start": week_start, "week_end": today, "generated_at": generated_at,
            "count": len(items), "items": items}
