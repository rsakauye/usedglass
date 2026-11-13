"""Weekly biggest-drop feed (scraper/dropsfeed.py). Run by the daily workflow as tests.test_dropsfeed."""
import json
import tempfile
import unittest
from pathlib import Path

from scraper import dropsfeed, run

TODAY = "2026-11-12"  # week_start is 2026-11-05


def listing(i, price, **kw):
    row = {"id": i, "title": f"Listing {i}", "dealer": "Test Camera", "url": f"https://example.invalid/{i}",
           "model_key": f"lens-{i}", "model_name": f"Model {i}", "category": "lens", "condition": "Good",
           "price_cad": price}
    row.update(kw)
    return row


def points(*pairs):
    return {"fs": pairs[0][0], "p": [list(p) for p in pairs], "ls": TODAY}


class WeekDropTests(unittest.TestCase):
    def test_baseline_is_last_price_on_or_before_week_start(self):
        pts = [["2026-10-20", 1000], ["2026-11-05", 900], ["2026-11-09", 800]]
        self.assertEqual(dropsfeed.week_drop(pts, "2026-11-05", TODAY), (900, 800, "2026-11-09"))

    def test_latest_price_wins_when_it_moved_twice(self):
        pts = [["2026-10-20", 1000], ["2026-11-07", 900], ["2026-11-10", 850]]
        self.assertEqual(dropsfeed.week_drop(pts, "2026-11-05", TODAY), (1000, 850, "2026-11-10"))

    def test_listing_first_seen_this_week_uses_its_first_price(self):
        pts = [["2026-11-08", 500], ["2026-11-11", 400]]
        self.assertEqual(dropsfeed.week_drop(pts, "2026-11-05", TODAY), (500, 400, "2026-11-11"))

    def test_no_change_inside_the_window(self):
        self.assertIsNone(dropsfeed.week_drop([["2026-10-20", 1000], ["2026-11-01", 800]], "2026-11-05", TODAY))
        self.assertIsNone(dropsfeed.week_drop([["2026-10-20", 1000]], "2026-11-05", TODAY))
        self.assertIsNone(dropsfeed.week_drop([], "2026-11-05", TODAY))


class BuildTests(unittest.TestCase):
    def build(self, rows, state):
        return dropsfeed.build(rows, state, TODAY, "2026-11-12T12:00:00+00:00")

    def test_mid_week_drops_are_included_and_ranked(self):
        rows = [listing("small", 900), listing("big", 600), listing("tie", 1200)]
        state = {
            "small": points(("2026-10-20", 1000), ("2026-11-09", 900)),   # 10%, $100
            "big": points(("2026-10-20", 1000), ("2026-11-10", 600)),     # 40%, $400
            "tie": points(("2026-10-20", 2000), ("2026-11-08", 1200)),    # 40%, $800: same percent, more dollars
        }
        out = self.build(rows, state)
        self.assertEqual([i["id"] for i in out["items"]], ["tie", "big", "small"])
        self.assertEqual((out["week_start"], out["week_end"], out["count"]), ("2026-11-05", TODAY, 3))
        self.assertEqual(out["generated_at"], "2026-11-12T12:00:00+00:00")
        self.assertEqual(out["items"][1], {
            "id": "big", "title": "Listing big", "dealer": "Test Camera", "url": "https://example.invalid/big",
            "model_key": "lens-big", "model_name": "Model big", "category": "lens",
            "old_price": 1000, "new_price": 600, "pct": 0.4, "saved_cad": 400,
            "drop_date": "2026-11-10", "model_path": "/model/lens-big/",
        })

    def test_rise_is_excluded(self):
        out = self.build([listing("up", 1100)], {"up": points(("2026-10-20", 1000), ("2026-11-09", 1100))})
        self.assertEqual(out["items"], [])

    def test_drop_over_70_percent_is_excluded(self):
        rows = [listing("mismatch", 250), listing("edge", 300)]
        state = {"mismatch": points(("2026-10-20", 1000), ("2026-11-09", 250)),   # 75%
                 "edge": points(("2026-10-20", 1000), ("2026-11-09", 300))}       # exactly 70% is kept, as in deals
        self.assertEqual([i["id"] for i in self.build(rows, state)["items"]], ["edge"])

    def test_fifty_dollars_counts_when_the_percent_is_small(self):
        rows = [listing("bigticket", 3940), listing("tiny", 990)]
        state = {"bigticket": points(("2026-10-20", 4000), ("2026-11-09", 3940)),  # 1.5%, $60
                 "tiny": points(("2026-10-20", 1000), ("2026-11-09", 990))}        # 1%, $10
        out = self.build(rows, state)
        self.assertEqual([i["id"] for i in out["items"]], ["bigticket"])
        self.assertEqual((out["items"][0]["pct"], out["items"][0]["saved_cad"]), (0.015, 60))

    def test_stale_and_as_is_are_skipped(self):
        drop = points(("2026-10-20", 1000), ("2026-11-09", 700))
        rows = [listing("stale", 700, stale=True), listing("asis", 700, condition="As Is"), listing("ok", 700)]
        out = self.build(rows, {"stale": drop, "asis": drop, "ok": drop})
        self.assertEqual([i["id"] for i in out["items"]], ["ok"])

    def test_listing_gone_from_todays_listings_is_not_in_the_feed(self):
        out = self.build([], {"sold": points(("2026-10-20", 1000), ("2026-11-09", 700))})
        self.assertEqual(out["items"], [])

    def test_drop_before_the_window_is_excluded(self):
        out = self.build([listing("old", 700)], {"old": points(("2026-10-20", 1000), ("2026-11-05", 700))})
        self.assertEqual(out["items"], [])

    def test_no_model_key_means_no_model_path(self):
        rows = [listing("bag", 60, model_key=None, model_name=None, category="accessory")]
        item = self.build(rows, {"bag": points(("2026-10-20", 100), ("2026-11-09", 60))})["items"][0]
        self.assertIsNone(item["model_key"])
        self.assertIsNone(item["model_path"])

    def test_capped_at_25(self):
        rows = [listing(f"l{n:02d}", 500 - n) for n in range(40)]
        state = {r["id"]: points(("2026-10-20", 1000), ("2026-11-09", r["price_cad"])) for r in rows}
        out = self.build(rows, state)
        self.assertEqual(out["count"], 25)
        self.assertEqual(len(out["items"]), 25)
        self.assertEqual(out["items"][0]["id"], "l39")

    def test_cents_are_rounded(self):
        out = self.build([listing("c", 149.95)], {"c": points(("2026-10-20", 199.99), ("2026-11-09", 149.95))})
        item = out["items"][0]
        self.assertEqual((item["old_price"], item["new_price"], item["saved_cad"], item["pct"]), (199.99, 149.95, 50.04, 0.25))

    def test_empty_input_writes_a_valid_empty_file(self):
        out = self.build([], {})
        self.assertEqual(out, {"week_start": "2026-11-05", "week_end": TODAY,
                               "generated_at": "2026-11-12T12:00:00+00:00", "count": 0, "items": []})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "biggest-drops.json"
            run.save(path, out)
            self.assertEqual(json.loads(path.read_text()), out)


if __name__ == "__main__":
    unittest.main()
