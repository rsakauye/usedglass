"""Dealer adapters. Each returns a list of normalized listings (see normalize.make_listing)."""
from __future__ import annotations

import csv
import html
import io
import json
import re

from .http import fetch
from .normalize import make_listing

DEALERS = {
    "thecamerastore": {"name": "The Camera Store", "city": "Calgary, AB", "site": "https://thecamerastore.com"},
    "mcbain": {"name": "McBain Camera", "city": "Edmonton, AB", "site": "https://www.mcbaincamera.com"},
    "beauphoto": {"name": "Beau Photo", "city": "Vancouver, BC", "site": "https://www.beauphoto.com"},
    "downtowncamera": {"name": "Downtown Camera", "city": "Toronto, ON", "site": "https://downtowncamera.com"},
    "gosselin": {"name": "Gosselin Photo", "city": "Quebec", "site": "https://gosselinphoto.ca"},
    "camtec": {"name": "Camtec Photo", "city": "Montreal, QC", "site": "https://www.camtecphoto.com"},
    "ebay": {"name": "eBay (Canadian sellers)", "city": "Canada", "site": "https://www.ebay.ca"},
}


def _shopify(dealer_id: str, base: str, collection: str, now: str, max_pages: int = 20) -> list[dict]:
    out = []
    name = DEALERS[dealer_id]["name"]
    for page in range(1, max_pages + 1):
        url = f"{base}/collections/{collection}/products.json?limit=250&page={page}"
        prods = json.loads(fetch(url))["products"]
        for p in prods:
            v = (p.get("variants") or [{}])[0]
            body = re.sub(r"<[^>]+>", " ", p.get("body_html") or "")[:600]
            img = (p.get("images") or [{}])[0].get("src") if p.get("images") else None
            out.append(make_listing(
                dealer_id, name, p["title"], v.get("price"), f"{base}/products/{p['handle']}",
                sku=str(v.get("id") or p["id"]), in_stock=v.get("available", True),
                condition_hint=" ".join(p.get("tags", [])) + " " + (v.get("title") or "") + " " + body,
                category_hint=p.get("product_type", ""), brand_hint=p.get("vendor", "") if p.get("vendor", "").lower() not in {"the camera store", "gosselin", "gosselin photo"} else "",
                fetched_at=now, image=img))
        if len(prods) < 250:
            break
    return out


def thecamerastore(now: str) -> list[dict]:
    return _shopify("thecamerastore", "https://thecamerastore.com", "pre-owned", now)


def gosselin(now: str) -> list[dict]:
    return _shopify("gosselin", "https://gosselinphoto.ca", "equipement-photo-video-usages", now)


def mcbain(now: str) -> list[dict]:
    base = "https://www.mcbaincamera.com/"
    h = fetch(base + "products.php?product_type=Used%20Equipment",
              data=b"sortResults=+product_id+DESC&hmd_results=1").decode("utf-8", "ignore")
    out, seen = [], set()
    rx = (r'<a href="(productdetail\.php\?mcbain_id=(U\d+))"><img src="([^"]+)"[^>]*>\s*</a>\s*'
          r'<h2><a href="productdetail\.php\?mcbain_id=U\d+"[^>]*>([^<]+)</a></h2>\s*<p>\s*<span class="[^"]*"[^>]*>\$([\d,\.]+)')
    rx2 = (r'<h2><a href="(productdetail\.php\?mcbain_id=(U\d+))"[^>]*>([^<]+)</a></h2>\s*<p>\s*'
           r'<span class="[^"]*"[^>]*>\$([\d,\.]+)')
    imgs = {m.group(2): m.group(3) for m in re.finditer(rx, h)}
    for m in re.finditer(rx2, h):
        sku = m.group(2)
        if sku in seen:
            continue
        seen.add(sku)
        img = imgs.get(sku)
        out.append(make_listing("mcbain", DEALERS["mcbain"]["name"], m.group(3), m.group(4), base + m.group(1),
                                sku=sku, fetched_at=now, image=(base + img) if img and not img.startswith("http") else img))
    return out


def downtowncamera(now: str) -> list[dict]:
    # Public Google Sheet linked from https://downtowncamera.com/used-equipment
    sheet = ("https://docs.google.com/spreadsheets/d/1XQx3uaeR_puoGsZn1MZtmdp4uBaZwDjUMf1vzLMlGmo/export?format=csv")
    rows = csv.DictReader(io.StringIO(fetch(sheet, check_robots=False).decode("utf-8", "ignore")))
    out, seen = [], set()
    for r in rows:
        r = {(k or "").strip(): (v or "") for k, v in r.items()}
        sku = r.get("STOCK #", "").strip()
        if not sku or sku in seen:
            continue
        seen.add(sku)
        brand = r.get("BRAND", "").replace("USED", "").strip(" -")
        desc = r.get("Description", "").strip(" -")
        title = desc if brand.lower() in desc.lower() else f"{brand.title()} {desc}"
        price = r.get("Selling  Price") or r.get("Selling Price")
        out.append(make_listing("downtowncamera", DEALERS["downtowncamera"]["name"], title, price,
                                "https://downtowncamera.com/used-equipment", sku=sku, fetched_at=now,
                                category_hint=r.get("Catergories", "").strip(" -"), brand_hint=brand,
                                condition_hint=r.get("Waranty", "")))
    return out


def beauphoto(now: str) -> list[dict]:
    out, page = [], 1
    while page <= 20:
        url = f"https://www.beauphoto.com/wp-json/wc/store/v1/products?category=1919&per_page=100&page={page}"
        prods = json.loads(fetch(url))
        for p in prods:
            pr = p.get("prices") or {}
            price = int(pr["price"]) / (10 ** pr.get("currency_minor_unit", 2)) if pr.get("price") else None
            desc = re.sub("<[^>]+>", " ", p.get("short_description") or "")[:400]  # long description has warranty boilerplate
            img = (p.get("images") or [{}])[0].get("src") if p.get("images") else None
            out.append(make_listing("beauphoto", DEALERS["beauphoto"]["name"], html.unescape(p["name"]), price,
                                    p["permalink"], sku=str(p["id"]), in_stock=p.get("is_in_stock", True),
                                    condition_hint=desc,
                                    category_hint=" ".join(c["name"] for c in p.get("categories", [])),
                                    fetched_at=now, image=img))
        if len(prods) < 100:
            break
        page += 1
    return out


def camtec(now: str) -> list[dict]:
    # robots.txt asks for Crawl-delay: 10 -> http.fetch honours it. One page with per-page=all.
    url = "https://www.camtecphoto.com/en/collections/pre-owned?per-page=all"
    h = fetch(url).decode("utf-8", "ignore")
    out = []
    for block in h.split('<li class="product-list-entry">')[1:]:
        m = re.search(r'<h2><a href="([^"]+)"[^>]*>([^<]+)</a></h2>', block)
        if not m:
            continue
        prices = re.findall(r'<span class="bold">\$([\d,\.]+)</span>', block) or re.findall(r"\$([\d,]+\.\d\d)", block)
        if not prices:
            continue
        img = re.search(r'<img src="([^"]+)"', block)
        desc = re.sub(r"<[^>]+>", " ", block)
        loc = re.search(r"Available at ([^<,]+)", block)
        sku = re.search(r'<p class="bold">([^<]+)</p>', block)
        out.append(make_listing("camtec", DEALERS["camtec"]["name"], m.group(2), prices[-1], m.group(1),
                                sku=m.group(1), fetched_at=now, condition_hint=desc[:600],
                                image=img.group(1) if img else None,
                                location=loc.group(1).strip() if loc else None))
    return out


ADAPTERS = {
    "mcbain": mcbain,
    "downtowncamera": downtowncamera,
    "gosselin": gosselin,
    "beauphoto": beauphoto,
    "thecamerastore": thecamerastore,
    "camtec": camtec,
}
