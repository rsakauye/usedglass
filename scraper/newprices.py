"""Canadian NEW-gear reference prices, used by the Deal Score (used vs new, successor gap) and the
"rate moved, prices haven't" currency signal.

Source: The Camera Store (Calgary) public Shopify storefront JSON for its "cameras" and "lenses" collections, the
same public endpoint and polite fetcher (robots.txt, >=2 s between requests, UsedGlassBot UA) already used for
its pre-owned collection. Only clean new items are kept: titles marked used / pre-owned / demo / open box / refurbished
are dropped, camera bundles ("with ...", "kit") are skipped when a body-only price exists, and titles whose version
marker (II, III, V, C ...) does not match the matched model key are dropped so a "Mark III" never prices a "Mark II".
Output: data/new-prices.json  {model_key: {name, price, title, url, dealer, first_seen, last_seen, history}}.
"""
from __future__ import annotations

import json
import re

from .http import fetch
from .normalize import make_listing

BASE = "https://thecamerastore.com"
DEALER = "The Camera Store"
COLLECTIONS = ("cameras", "lenses")
MAX_PAGES = 12
SKIP_RX = re.compile(r"\b(used|pre-?owned|demo|open[- ]?box|refurb\w*|b-?stock|rental|consign\w*|ex-?display)\b|\*", re.I)
BUNDLE_RX = re.compile(r"\bwith\b|\bw/|\bkit\b|\bbundle\b|\+", re.I)
ROMAN_RX = re.compile(r"\b(?:mark\s*)?(II|III|IV|V|VI)\b|\bmk\.?\s*(2|3|4|5|6)\b|\b[a-z]+\d+(II|III|IV|V|VI)\b", re.I)
SUFFIX_RX = re.compile(r"\b[A-Z]{1,2}\d{1,3}\s+(C|V|N)\b")  # "EOS R5 C", "EOS R6 V": different cameras
ARABIC = {"2": "ii", "3": "iii", "4": "iv", "5": "v", "6": "vi"}


def _version_ok(title: str, key: str, category: str) -> bool:
    if category != "camera":
        return True
    sm = SUFFIX_RX.search(title)
    if sm and not key.endswith("-" + sm.group(1).lower()):
        return False
    m = ROMAN_RX.search(title)
    ver = None
    if m:
        ver = (m.group(1) or ARABIC.get(m.group(2) or "", "") or m.group(3) or "").lower() or None
    key_ver = next((v for v in ("vi", "iv", "iii", "ii", "v") if key.endswith("-" + v) or key.endswith(v)), None)
    if ver:
        return key.endswith(ver)
    return key_ver is None or not re.search(r"-(ii|iii|iv|v|vi)$", key)


def fetch_new(now: str, exclude_urls: set[str] | None = None) -> list[dict]:
    exclude_urls = exclude_urls or set()
    rows = []
    for col in COLLECTIONS:
        for page in range(1, MAX_PAGES + 1):
            prods = json.loads(fetch(f"{BASE}/collections/{col}/products.json?limit=250&page={page}"))["products"]
            for p in prods:
                title = p.get("title") or ""
                url = f"{BASE}/products/{p['handle']}"
                tags = p.get("tags", [])
                tags = [t.strip() for t in tags.split(",")] if isinstance(tags, str) else tags
                if url in exclude_urls or SKIP_RX.search(title) or any(SKIP_RX.search(t or "") for t in tags):
                    continue
                v = (p.get("variants") or [{}])[0]
                if not v.get("available", True):
                    continue
                x = make_listing("thecamerastore-new", DEALER, title, v.get("price"), url, sku=str(v.get("id") or p["id"]),
                                 category_hint=p.get("product_type", ""), brand_hint=p.get("vendor") or "", fetched_at=now)
                if not x.get("model_key") or not x.get("price_cad") or x["category"] not in ("camera", "lens"):
                    continue
                if not _version_ok(title, x["model_key"], x["category"]):
                    continue
                x["bundle"] = bool(BUNDLE_RX.search(title)) and x["category"] == "camera"
                rows.append(x)
            if len(prods) < 250:
                break
    return rows


def pick(rows: list[dict]) -> dict[str, dict]:
    """Cheapest clean listing per model key; for cameras prefer body-only over bundles."""
    best: dict[str, dict] = {}
    for x in rows:
        mk = x["model_key"]
        cur = best.get(mk)
        rank = (x["bundle"], x["price_cad"])
        if cur is None or rank < (cur["bundle"], cur["price_cad"]):
            best[mk] = x
    return best


def update(prev: dict, rows: list[dict], today: str) -> dict:
    out = {}
    cur = pick(rows)
    for mk, x in cur.items():
        p = prev.get(mk) or {}
        hist = list(p.get("history") or [])
        if not hist or hist[-1][1] != x["price_cad"]:
            hist.append([today, x["price_cad"]])
        out[mk] = {"name": x["model_name"], "category": x["category"], "price": x["price_cad"], "title": x["title"],
                   "url": x["url"], "dealer": DEALER, "bundle": x["bundle"], "first_seen": p.get("first_seen", today),
                   "last_seen": today, "history": hist[-200:]}
    for mk, p in prev.items():  # keep models that vanished (out of stock) for 60 days, marked as not current
        if mk not in out and p.get("last_seen", today) >= _days_ago(today, 60):
            out[mk] = p
    return out


def _days_ago(today: str, n: int) -> str:
    import datetime as dt
    return (dt.date.fromisoformat(today) - dt.timedelta(days=n)).isoformat()
