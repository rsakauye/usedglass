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


if __name__ == "__main__":
    unittest.main()
