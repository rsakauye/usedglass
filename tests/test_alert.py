import unittest

from scraper.alert import problems, report


class AlertTests(unittest.TestCase):
    def test_problem_detection(self):
        meta = {"date": "2026-10-18", "dealers": {
            "ok": {"count": 100, "status": "ok"},
            "broken": {"count": 40, "status": "error - kept previous listings"},
            "drop": {"count": 5, "status": "ok", "warning": "listing count fell from 300 to 5"},
            "zero": {"count": 0, "status": "ok"},
            "ebay": {"count": 0, "status": "skipped (no API keys)"},
        }, "errors": {"broken": "HTTPError: HTTP Error 404: Not Found"}}
        got = {p["dealer"]: p["problem"] for p in problems(meta)}
        self.assertEqual(set(got), {"broken", "drop", "zero"})
        self.assertIn("404", got["broken"])
        self.assertIn("broken", report(meta, problems(meta)))

    def test_all_healthy(self):
        meta = {"dealers": {"a": {"count": 3, "status": "ok"}, "ebay": {"count": 0, "status": "skipped (no API keys)"}}}
        self.assertEqual(problems(meta), [])
        self.assertIn("healthy", report(meta, []))

    def test_paused_is_not_a_scrape_error(self):
        meta = {"date": "2026-11-05", "dealers": {
            "plotcamera": {"count": 0, "status": "paused (ToS: scrape ban)"},
            "cameratraders": {"count": 0, "status": "paused (ToS: scrape ban)"},
            "maplecamera": {"count": 0, "status": "paused (ToS: scrape ban)"},
            "mcbain": {"count": 10, "status": "ok"},
        }, "errors": {}, "total": 10}
        self.assertEqual(problems(meta), [])
        text = report(meta, [])
        self.assertIn("not failures", text)
        self.assertIn("plotcamera", text)
        self.assertNotIn("| Dealer | Problem |", text)

    def test_paused_does_not_hide_a_real_error(self):
        meta = {"dealers": {
            "plotcamera": {"count": 0, "status": "paused (ToS: scrape ban)"},
            "broken": {"count": 4, "status": "error - kept previous listings"},
        }, "errors": {"broken": "HTTPError: 404"}}
        got = problems(meta)
        self.assertEqual([p["dealer"] for p in got], ["broken"])
        self.assertIn("404", report(meta, got))
        self.assertIn("plotcamera", report(meta, got))


if __name__ == "__main__":
    unittest.main()
