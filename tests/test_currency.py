import json
import os
import unittest
from unittest import mock

from scraper import currency, dealscore


FX = {"latest": {"USD": {"date": "2026-10-16", "rate": 1.40, "chg_30d": 0.03}}}


class CurrencyTests(unittest.TestCase):
    def test_summarize_changes(self):
        hist = [["2026-09-15", 1.36], ["2026-10-09", 1.40], ["2026-10-16", 1.428]]
        s = currency.summarize(hist)
        self.assertEqual(s["rate"], 1.428)
        self.assertAlmostEqual(s["chg_7d"], 0.02, places=3)
        self.assertAlmostEqual(s["chg_30d"], 0.05, places=3)
        self.assertIn("weakened", currency.describe("USD", s))

    def test_landed_cost(self):
        est = currency.landed_cad(1000, "USD", FX, ship=40, brokerage=25)
        self.assertEqual(est["goods_cad"], 1400)
        self.assertEqual(est["tax_cad"], round((1400 + 40) * 0.05, 2))
        self.assertEqual(est["landed_cad"], round(1400 + 40 + 25 + 72, 2))

    def test_gap_flags_only_meaningful_savings(self):
        np = {"camera-x": {"name": "X", "price": 2000, "dealer": "D", "url": "u"}}
        offers = [{"model_key": "camera-x", "price": 1000, "currency": "USD", "seller": "US", "url": "v"},
                  {"model_key": "camera-x", "price": 1300, "currency": "USD", "seller": "US2", "url": "w"}]
        g = {x["seller"]: x for x in currency.currency_gap(offers, np, {}, {}, FX)}
        self.assertTrue(g["US"]["flagged"])
        self.assertFalse(g["US2"]["flagged"])  # 1300 USD lands above 2000 CAD

    def test_rate_moved_needs_history_and_threshold(self):
        np = {"camera-x": {"name": "X", "price": 2000, "dealer": "D", "url": "u", "first_seen": "2026-09-01",
                           "last_seen": "2026-10-18", "history": [["2026-09-01", 2000]]},
              "camera-y": {"name": "Y", "price": 900, "dealer": "D", "url": "u", "first_seen": "2026-09-01",
                           "last_seen": "2026-10-18", "history": [["2026-09-01", 950], ["2026-10-10", 900]]}}
        r = currency.rate_moved(np, FX, "2026-10-18")
        self.assertEqual(r["direction"], "cad_weaker")
        self.assertEqual([i["model_key"] for i in r["items"]], ["camera-x"])
        self.assertIn("may rise", r["status"])
        small = {"latest": {"USD": {"rate": 1.4, "chg_30d": 0.01}}}
        self.assertEqual(currency.rate_moved(np, small, "2026-10-18")["items"], [])

    def test_currency_gap_records_never_contain_a_username(self):
        """Browse API offers, gap rows, and the deal built from them keep a fixed label."""
        fixture = "ZZ-NOT-A-REAL-ACCOUNT"
        import inspect
        src = inspect.getsource(currency.ebay_us_offers)
        for access in ('["username"]', "['username']", '.get("username")', ".get('username')"):
            self.assertNotIn(access, src)
        item = {
            "title": "Sony A7 III Body (EX)",
            "price": {"value": "999.00", "currency": "USD"},
            "itemWebUrl": "https://www.ebay.com/itm/100",
            "seller": {"username": fixture, "feedbackScore": 10},
            "shippingOptions": [{"shippingCost": {"value": "12.50", "currency": "USD"}}],
        }
        payload = json.dumps({"itemSummaries": [item]}).encode()

        def fake_fetch(url, headers=None, check_robots=True):
            self.assertNotIn(fixture, url)
            self.assertFalse(check_robots)
            return payload

        env = {"EBAY_CLIENT_ID": "app-id", "EBAY_CLIENT_SECRET": "app-secret", "EBAY_US_GAP": "1"}
        with mock.patch.dict(os.environ, env), mock.patch("scraper.ebay._token", return_value="tok"), \
                mock.patch("scraper.currency.fetch", side_effect=fake_fetch):
            offers = currency.ebay_us_offers({"camera-sony-a7-iii": "Sony A7 III"}, "2026-10-26T00:00:00Z")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["seller"], currency.EBAY_US_SELLER)
        self.assertEqual(offers[0]["ship_usd"], 12.5)
        self.assertNotIn(fixture, json.dumps(offers))
        self.assertNotIn("username", json.dumps(offers))

        np = {"camera-sony-a7-iii": {"name": "Sony A7 III", "price": 2000, "dealer": "D", "url": "https://example.invalid/ca"}}
        gaps = currency.currency_gap(offers, np, {}, {}, FX)
        self.assertEqual(gaps[0]["seller"], "eBay US seller")
        self.assertNotIn(fixture, json.dumps(gaps))
        deal = currency.gap_deal(gaps[0], "2026-10-26T00:00:00Z")
        self.assertEqual(deal["dealer"], "eBay US seller")
        self.assertNotIn(fixture, json.dumps(deal))
        self.assertNotIn("eBay US:", json.dumps(deal))

        legacy = [{"model_key": "camera-x", "price": 1000, "currency": "USD", "condition": "new",
                   "seller": "eBay US: " + fixture, "url": "https://example.invalid/item"}]
        rewritten = currency.currency_gap(legacy, {"camera-x": {"name": "X", "price": 2000, "dealer": "D", "url": "u"}}, {}, {}, FX)
        self.assertEqual(rewritten[0]["seller"], "eBay US seller")
        blob = json.dumps(rewritten) + json.dumps(currency.gap_deal(rewritten[0], "2026-10-26T00:00:00Z"))
        self.assertNotIn(fixture, blob)
        self.assertNotIn("eBay US:", blob)
        raw = dict(rewritten[0], seller="eBay US: " + fixture)
        raw_deal = currency.gap_deal(raw, "2026-10-26T00:00:00Z")
        self.assertEqual(raw_deal["dealer"], "eBay US seller")
        self.assertNotIn(fixture, json.dumps(raw_deal))

    def test_shop_seller_names_are_kept(self):
        offers = [{"model_key": "camera-x", "price": 1000, "currency": "USD", "seller": "Example Shop", "url": "v"}]
        g = currency.currency_gap(offers, {"camera-x": {"name": "X", "price": 2000, "dealer": "D", "url": "u"}}, {}, {}, FX)
        self.assertEqual(g[0]["seller"], "Example Shop")
        self.assertEqual(currency.gap_deal(g[0], "2026-10-26T00:00:00Z")["dealer"], "Example Shop")


class DealScoreTests(unittest.TestCase):
    META = {"camera-a": {"name": "A", "announced": "2020-07-09", "successor": "camera-a-ii"},
            "camera-a-ii": {"name": "A II", "announced": "2025-11-06"}}
    NEW = {"camera-a": {"price": 3000, "dealer": "D"}, "camera-a-ii": {"price": 3300, "dealer": "D", "name": "A II"}}

    def test_black_friday(self):
        self.assertEqual(dealscore.black_friday(2026).isoformat(), "2026-11-27")

    def test_history_only_fallback(self):
        x = {"price_cad": 750, "model_key": "lens-z", "title": "Lens Z", "category": "lens"}
        s = dealscore.score_listing(x, [1000, 1000, 1000], None, 0, {}, {}, "2026-10-18")
        self.assertEqual(s["score"], 100)
        self.assertIn("history only", s["basis"])

    def test_successor_better_value(self):
        x = {"price_cad": 3000, "model_key": "camera-a", "title": "A body", "category": "camera"}
        s = dealscore.score_listing(x, [3000, 3000, 3000], None, 0, self.NEW, self.META, "2026-10-18")
        self.assertTrue(any("better value" in w for w in s["why"]))
        self.assertLess(s["score"], 45)

    def test_bundle_not_compared_with_body_price(self):
        x = {"price_cad": 3200, "model_key": "camera-a", "title": "A with 24-105 kit", "category": "camera"}
        s = dealscore.score_listing(x, [3000, 3100, 3300], None, 0, self.NEW, self.META, "2026-10-18")
        self.assertNotIn("vs_new", s["parts"])

    def test_no_event_low_before_event_happens(self):
        h = [["2026-10-18", 2499]]
        self.assertIsNone(dealscore.event_low(h, "2026-10-18", dealscore.sale_events("2026-10-18", "2026-10-18"), "2026-10-18"))


if __name__ == "__main__":
    unittest.main()
