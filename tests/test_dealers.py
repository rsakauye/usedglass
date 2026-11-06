import inspect
import unittest

from scraper.dealers import ADAPTERS, DEALERS, PAUSED_DEALERS, dealer_info, downtowncamera, paused_meta
from scraper.run import scrape_picks

PAUSED_IDS = ("plotcamera", "cameratraders", "maplecamera")


class PausedDealerTests(unittest.TestCase):
    def test_pause_set_keeps_adapters_and_names(self):
        self.assertEqual(set(PAUSED_DEALERS), set(PAUSED_IDS))
        for dealer_id in PAUSED_IDS:
            self.assertIn(dealer_id, ADAPTERS)
            self.assertTrue(callable(ADAPTERS[dealer_id]))
            self.assertIn("name", DEALERS[dealer_id])
            self.assertIn("site", DEALERS[dealer_id])
            meta = paused_meta(dealer_id)
            self.assertEqual(meta["count"], 0)
            self.assertEqual(meta["status"], "paused (ToS: scrape ban)")
            self.assertTrue(meta["status"].startswith("paused"))
            info = dealer_info()[dealer_id]
            self.assertEqual(info["name"], DEALERS[dealer_id]["name"])
            self.assertEqual(info["paused"], meta["status"])
        self.assertIsNone(paused_meta("mcbain"))
        self.assertNotIn("paused", dealer_info()["downtowncamera"])

    def test_default_run_records_paused_dealers_without_dropping_them_from_the_set(self):
        picks = scrape_picks([])
        self.assertEqual(picks, list(ADAPTERS) + ["ebay"])
        for dealer_id in PAUSED_IDS:
            self.assertIn(dealer_id, picks)
        # A one-dealer run does not invent the paused ids, and "newprices" is not a dealer.
        self.assertEqual(scrape_picks(["mcbain", "newprices"]), ["mcbain"])
        # Naming a paused dealer still selects it; paused_meta is what skips the fetch.
        self.assertEqual(scrape_picks(["plotcamera"]), ["plotcamera"])

    def test_downtown_sheet_honours_robots(self):
        src = inspect.getsource(downtowncamera)
        self.assertNotIn("check_robots=False", src)
        self.assertIn("fetch(sheet)", src)


if __name__ == "__main__":
    unittest.main()
