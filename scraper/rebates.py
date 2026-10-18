"""Manufacturer rebate / instant-savings tracker for Canada (heuristic, AI-free).

Fetches official Canadian promo index pages, follows promo links, extracts title, date range and
"up to $X" amounts. Anything not parsed confidently is still listed with a link for a human check.
"""
from __future__ import annotations

import html
import re

from .http import fetch

SOURCES = [
    {"brand": "Canon", "index": "https://www.canoncreatorlab.ca/offers/",
     "link_rx": r'href="(https://www\.canoncreatorlab\.ca/offers/[^"#?]+/)"'},
    {"brand": "Fujifilm", "index": "https://www.fujifilm-x.com/en-ca/promotions/",
     "link_rx": r'href="(https://www\.fujifilm-x\.com/en-ca/[a-z0-9-]*(?:promotion|save|rebate|offer)[a-z0-9-]*/)"'},
    {"brand": "Nikon", "index": "https://en.nikon.ca/content/rebate-program", "link_rx": None},
]
MANUAL_CHECK = [
    {"brand": "Sony", "url": "https://www.sony.ca/en/promotions", "note": "sony.ca blocks automated fetches; check manually"},
    {"brand": "Nikon", "url": "https://store.nikon.ca/products-on-sale/", "note": "JS-rendered instant savings list"},
]
DATE_RX = (r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,\s*\d{4})?|\d{1,2}/\d{1,2}/\d{4})"
           r"\s*(?:-|–|to|through|until)\s*"
           r"((?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4})")
AMOUNT_RX = r"(?:up to|save|get)\s+(?:up to\s+)?\$\s?([\d,]+)"


def _text(h: str) -> str:
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


def _parse(brand: str, url: str, h: str, now: str) -> dict:
    title = re.search(r"<title>([^<]+)</title>", h, re.I)
    t = _text(h)
    d = re.search(DATE_RX, t, re.I)
    amts = [int(a.replace(",", "")) for a in re.findall(AMOUNT_RX, t, re.I)]
    return {
        "brand": brand, "url": url,
        "title": html.unescape(title.group(1)).split("|")[0].strip() if title else url,
        "starts": d.group(1) if d else None, "ends": d.group(2) if d else None,
        "max_amount_cad": max(amts) if amts else None, "fetched_at": now,
    }


def rebates(now: str) -> dict:
    items, errors = [], []
    for s in SOURCES:
        try:
            h = fetch(s["index"]).decode("utf-8", "ignore")
            links = sorted(set(re.findall(s["link_rx"], h))) if s["link_rx"] else [s["index"]]
            links = [u for u in links if u.rstrip("/") != s["index"].rstrip("/")][:8] or [s["index"]]
            for u in links:
                ph = h if u == s["index"] else fetch(u).decode("utf-8", "ignore")
                items.append(_parse(s["brand"], u, ph, now))
        except Exception as e:  # keep going; one broken source should not kill the run
            errors.append({"brand": s["brand"], "error": f"{type(e).__name__}: {e}"})
    return {"fetched_at": now, "items": items, "manual_check": MANUAL_CHECK, "errors": errors}
