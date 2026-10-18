"""eBay Browse API adapter (official API). Skips gracefully when credentials are absent.

Needs: EBAY_CLIENT_ID, EBAY_CLIENT_SECRET (eBay Developer Program production keyset).
Optional: EBAY_CAMPAIGN_ID (eBay Partner Network campaign id) -> affiliate-tracked itemAffiliateWebUrl.
Docs: https://developer.ebay.com/api-docs/buy/browse/resources/item_summary/methods/search
"""
from __future__ import annotations

import base64
import json
import os
import urllib.parse

from .http import fetch
from .normalize import make_listing

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
# eBay category ids: 3323 = Lenses & Filters > Lenses, 31388 = Digital Cameras, 15230 = Film Photography (cameras)
CATEGORIES = {"3323": "lens", "31388": "camera", "15230": "camera"}
CONDITION_MAP = {"3000": "", "2750": "Like New", "2990": "Excellent", "3010": "Good", "2500": "Like New", "7000": "As Is"}
MAX_PER_CATEGORY = int(os.environ.get("EBAY_MAX_PER_CATEGORY", "1000"))


def _token(cid: str, secret: str) -> str:
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials",
                                   "scope": "https://api.ebay.com/oauth/api_scope"}).encode()
    r = json.loads(fetch(TOKEN_URL, data=body, headers={"Authorization": f"Basic {auth}"}, check_robots=False))
    return r["access_token"]


def ebay(now: str) -> list[dict]:
    cid, secret = os.environ.get("EBAY_CLIENT_ID"), os.environ.get("EBAY_CLIENT_SECRET")
    if not cid or not secret:
        print("ebay: EBAY_CLIENT_ID/EBAY_CLIENT_SECRET not set -> skipped")
        return []
    tok = _token(cid, secret)
    headers = {"Authorization": f"Bearer {tok}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_CA",
               "Accept-Language": "en-CA"}
    camp = os.environ.get("EBAY_CAMPAIGN_ID")
    if camp:
        headers["X-EBAY-C-ENDUSERCTX"] = f"affiliateCampaignId={camp}"
    out = []
    for cat, kind in CATEGORIES.items():
        offset = 0
        while offset < MAX_PER_CATEGORY:
            q = {
                "category_ids": cat,
                "filter": "itemLocationCountry:CA,conditions:{USED},buyingOptions:{FIXED_PRICE},"
                          "priceCurrency:CAD,price:[60..]",
                "sort": "newlyListed", "limit": "200", "offset": str(offset),
            }
            r = json.loads(fetch(SEARCH_URL + "?" + urllib.parse.urlencode(q), headers=headers, check_robots=False))
            items = r.get("itemSummaries", [])
            for it in items:
                price = (it.get("price") or {}).get("value")
                if (it.get("price") or {}).get("currency", "CAD") != "CAD":
                    continue
                url = it.get("itemAffiliateWebUrl") or it.get("itemWebUrl")
                cond = CONDITION_MAP.get(str(it.get("conditionId")), "")
                loc = (it.get("itemLocation") or {})
                out.append(make_listing("ebay", "eBay (Canadian sellers)", it.get("title", ""), price, url,
                                        sku=it.get("itemId"), fetched_at=now, source="marketplace",
                                        condition_hint=f"{cond} {it.get('condition', '')}", category_hint=kind,
                                        image=(it.get("image") or {}).get("imageUrl"),
                                        location=", ".join(x for x in [loc.get("city"), loc.get("stateOrProvince")] if x) or None))
            offset += 200
            if len(items) < 200 or offset >= int(r.get("total", 0)):
                break
    return out
