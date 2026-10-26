"""Firmware builder helpers (scripts/firmware.py), model price stats (scraper/run.py) and the shape of the
hand-checked data the site renders (firmware notes, model summaries). Loaded via tests/test_normalize.load_tests.
First drafted by qwen2.5-coder; most expectations were wrong and were rewritten by hand."""
import importlib.util
import json
import pathlib
import re
import unittest

from scraper.run import floor_cheap_cameras, iso_minus, price_stats, update_model_seen

ROOT = pathlib.Path(__file__).resolve().parent.parent
_s = importlib.util.spec_from_file_location("fw", ROOT / "scripts" / "firmware.py")
fw = importlib.util.module_from_spec(_s)
_s.loader.exec_module(fw)


class FirmwareHelperTests(unittest.TestCase):
    def test_mdy(self):
        self.assertEqual(fw.mdy("Apr. 25, 2022"), "2022-04-25")
        self.assertEqual(fw.mdy("Nov. 04, 2025"), "2025-11-04")
        self.assertEqual(fw.mdy("September 3, 2026"), "2026-09-03")
        self.assertIsNone(fw.mdy("Invalid date"))
        self.assertIsNone(fw.mdy("Foo. 3, 2026"))

    def test_lens_sig(self):
        self.assertEqual(fw.lens_sig("Nikon 70-200mm f/2.8 STAB S (Nikon Z)"), ("70-200", "28", False))
        self.assertEqual(fw.lens_sig("Fujifilm 16-55mm f/2.8 LM II (Fujifilm X)"), ("16-55", "28", True))
        self.assertEqual(fw.lens_sig("Olympus 12-40mm f/2.8 PRO (Micro Four Thirds)"), ("12-40", "28", False))
        self.assertIsNone(fw.lens_sig("Fujifilm EF-X500 flash"))

    def test_match_lens(self):
        cands = [("16-55", "28", True, {"v": "II"}), ("16-55", "28", False, {"v": "I"}), ("50", "18", False, {"v": "a"}),
                 ("50", "18", False, {"v": "b"})]
        self.assertEqual(fw.match_lens(("16-55", "28", True), cands), {"v": "II"})
        self.assertEqual(fw.match_lens(("16-55", "28", False), cands), {"v": "I"})  # Mark I and II kept apart
        self.assertIsNone(fw.match_lens(("50", "18", False), cands))  # two different payloads: ambiguous
        self.assertIsNone(fw.match_lens(("16-55", "", False), cands))  # no aperture: never guess
        self.assertIsNone(fw.match_lens(None, cands))

    def test_table_rows(self):
        t = "| E-M1 Mark III | Ver.2.7 | Apr. 25, 2022 |\n| OM-1 / OM-1 Mark II | 1.9 | Click here | Nov. 04, 2025 |"
        rows = fw.table_rows(t)
        self.assertEqual(rows["em1markiii"][:2], ("2.7", "2022-04-25"))
        self.assertEqual(rows["om1"][:2], ("1.9", "2025-11-04"))
        self.assertEqual(rows["om1markii"][:2], ("1.9", "2025-11-04"))

    def test_carry_curated_keeps_footnote_for_same_version(self):
        old = {"version": "5.30", "footnote": {"text": "Use the FUJIFILM XApp.", "url": "https://example.com/x-h2/"}}
        new = {"version": "5.30", "released": "2025-12-02", "url": "https://example.com/x-h2/"}
        fw.carry_curated(old, new)
        self.assertEqual(new["footnote"], {"text": "Use the FUJIFILM XApp.", "url": "https://example.com/x-h2/"})

    def test_carry_curated_drops_hand_notes_when_version_changes(self):
        old = {"version": "5.30", "attention": "Pulled.", "attention_source": "https://example.com/a",
               "notes": "Old.", "notes_quotes": ["q"], "notes_source": "https://example.com/n",
               "footnote": {"text": "Use the FUJIFILM XApp.", "url": "https://example.com/x-h2/"}}
        new = {"version": "5.31", "url": "https://example.com/x-h2/"}
        fw.carry_curated(old, new)
        self.assertNotIn("footnote", new)
        self.assertNotIn("attention", new)
        self.assertNotIn("notes", new)

    def test_carry_curated_keeps_attention_and_notes(self):
        old = {"version": "1.0", "attention": "Bricking.", "attention_source": "https://example.com/a",
               "notes": "Fixes a bug.", "notes_quotes": ["quote"], "notes_source": "https://example.com/n"}
        new = {"version": "1.0"}
        fw.carry_curated(old, new)
        self.assertEqual((new["attention"], new["attention_source"]), ("Bricking.", "https://example.com/a"))
        self.assertEqual(new["notes"], "Fixes a bug.")
        self.assertEqual(new["notes_quotes"], ["quote"])
        self.assertEqual(new["notes_source"], "https://example.com/n")
        self.assertNotIn("footnote", new)

    def test_carry_curated_ignores_a_footnote_without_text(self):
        new = {"version": "1.0"}
        fw.carry_curated({"version": "1.0", "footnote": {"url": "https://example.com/"}}, new)
        fw.carry_curated({"version": "1.0", "footnote": "plain string"}, new)
        self.assertNotIn("footnote", new)


class PriceStatsTests(unittest.TestCase):
    def test_median_ignores_bundles_min_keeps_them(self):
        xs = [{"price_cad": 1000}, {"price_cad": 1200}, {"price_cad": 900, "bundle": True}, {"price_cad": 1800, "bundle": True}]
        self.assertEqual(price_stats(xs), {"count": 4, "min_price": 900, "median_price": 1100})

    def test_all_bundles_uses_all(self):
        xs = [{"price_cad": 1000, "bundle": True}, {"price_cad": 1400, "bundle": True}]
        self.assertEqual(price_stats(xs)["median_price"], 1200)

    def test_floor_cheap_camera_to_accessory(self):
        xs = [{"id": f"a{i}", "model_key": "camera-canon-r5", "model_name": "Canon R5", "category": "camera", "price_cad": p}
              for i, p in enumerate((2100, 2995, 3200))]
        xs.append({"id": "grip", "model_key": "camera-canon-r5", "model_name": "Canon R5", "category": "camera", "price_cad": 199})
        lens = {"id": "l", "model_key": "lens-x", "model_name": "X", "category": "lens", "price_cad": 5}
        xs.append(lens)
        state = {"grip": {"mk": "camera-canon-r5"}, "a0": {"mk": "camera-canon-r5"}}
        floor_cheap_cameras(xs, state)
        self.assertEqual((xs[3]["category"], xs[3]["model_key"], state["grip"]["mk"]), ("accessory", None, None))
        self.assertEqual(xs[0]["model_key"], "camera-canon-r5")
        self.assertEqual(state["a0"]["mk"], "camera-canon-r5")
        self.assertEqual(lens["model_key"], "lens-x")  # lenses are never floored

    def test_floor_ignores_bundle_prices_in_median(self):
        xs = [{"id": "body", "model_key": "m", "model_name": "M", "category": "camera", "price_cad": 300},
              {"id": "kit", "model_key": "m", "model_name": "M", "category": "camera", "price_cad": 5000, "bundle": True}]
        floor_cheap_cameras(xs, {})
        self.assertEqual(xs[0]["model_key"], "m")  # only the body-only listing counts as "others" for the kit


class SiteDataShapeTests(unittest.TestCase):
    def test_firmware_notes_are_quoted(self):
        doc = json.loads((ROOT / "data" / "firmware.json").read_text())
        for k, e in doc["models"].items():
            with self.subTest(model=k):
                self.assertRegex(e["released"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertTrue(e["url"].startswith("https://"))
                if e.get("notes"):
                    self.assertTrue(e.get("notes_quotes"), "every note needs its supporting quotes")
                    self.assertTrue(e["notes"].endswith("."))
                    self.assertLessEqual(len(e["notes"]), 220)
                foot = e.get("footnote")
                if foot:
                    self.assertIsInstance(foot, dict)
                    self.assertTrue(foot.get("text", "").endswith("."))
                    self.assertLessEqual(len(foot["text"]), 280)
                    self.assertTrue(foot.get("url", "").startswith("https://"))
                    self.assertNotIn("⚠️", foot["text"])
        xh2, xh2s = doc["models"]["camera-fujifilm-xh2"], doc["models"]["camera-fujifilm-xh2s"]
        self.assertEqual((xh2["version"], xh2s["version"]), ("5.30", "7.30"))
        self.assertIn("FUJIFILM XApp", xh2["footnote"]["text"])
        self.assertEqual(xh2["footnote"]["text"], xh2s["footnote"]["text"])
        self.assertEqual(xh2["footnote"]["url"], "https://www.fujifilm-x.com/global/support/download/firmware/cameras/x-h2/")
        self.assertEqual(xh2s["footnote"]["url"], "https://www.fujifilm-x.com/global/support/download/firmware/cameras/x-h2s/")
        self.assertNotIn("footnote", doc["models"]["camera-fujifilm-xh1"])

    def test_model_summaries_are_sourced(self):
        doc = json.loads((ROOT / "data" / "model-summaries.json").read_text())
        for k, e in doc["models"].items():
            with self.subTest(model=k):
                self.assertTrue(e["text"] and e["sources"] and e["source_fields"])
                self.assertTrue(all(u.startswith("https://") for u in e["sources"]))
                self.assertNotRegex(e["text"].lower(), r"\bno (in-body|ibis)\b")  # absence of a spec is never stated
                for n in re.findall(r"\b\d{3,}\b", e["text"].replace(",", "")):
                    self.assertNotIn(n, {"2024", "2025", "2026"}, "no dates in summaries")


class ModelSeenTests(unittest.TestCase):
    TODAY = "2026-10-26"

    def _live(self, **kw):
        m = {"name": "Canon EOS R5", "category": "camera", "brand": "Canon", "mount": "Canon RF",
             "min_price": 2800, "median_90d": 3000, "observations_90d": 4}
        m.update(kw)
        return m

    def test_live_model_stamps_today_and_price(self):
        out = update_model_seen({}, {"camera-canon-r5": self._live()}, {}, self.TODAY)
        row = out["camera-canon-r5"]
        self.assertEqual(row["last_seen"], self.TODAY)
        self.assertEqual(row["last_price"], 2800)
        self.assertEqual(row["median_90d"], 3000)
        self.assertEqual(row["median_90d_as_of"], self.TODAY)
        self.assertEqual((row["name"], row["brand"], row["mount"]), ("Canon EOS R5", "Canon", "Canon RF"))

    def test_dropped_model_keeps_recorded_price_inside_window(self):
        prev = {"lens-canon-35mm-f2_8": {
            "name": "Canon 35mm f/2.8", "category": "lens", "brand": "Canon", "mount": None,
            "last_seen": "2026-10-24", "last_price": 239.99, "median_90d": 239.99,
            "observations_90d": 1, "median_90d_as_of": "2026-10-24",
        }}
        out = update_model_seen(prev, {}, {}, self.TODAY)
        self.assertEqual(out["lens-canon-35mm-f2_8"]["last_price"], 239.99)
        self.assertEqual(out["lens-canon-35mm-f2_8"]["last_seen"], "2026-10-24")
        self.assertNotIn("camera-canon-r5", out)

    def test_state_refreshes_last_price_without_inventing_a_name(self):
        prev = {"lens-x": {"name": "X 50mm", "category": "lens", "brand": "X", "mount": None,
                           "last_seen": "2026-10-20", "last_price": 100, "median_90d": 100,
                           "observations_90d": 1, "median_90d_as_of": "2026-10-20"}}
        state = {
            "a": {"mk": "lens-x", "ls": "2026-10-22", "p": [["2026-10-20", 100], ["2026-10-22", 80]]},
            "b": {"mk": "lens-x", "ls": "2026-10-22", "p": [["2026-10-22", 120]]},
            "c": {"mk": "lens-unknown", "ls": "2026-10-22", "p": [["2026-10-22", 50]]},
        }
        out = update_model_seen(prev, {}, state, self.TODAY)
        self.assertEqual(out["lens-x"]["last_seen"], "2026-10-22")
        self.assertEqual(out["lens-x"]["last_price"], 80)  # cheapest copy on the last day
        self.assertEqual(out["lens-x"]["median_90d"], 100)  # median of 80 and 120
        self.assertEqual(out["lens-x"]["observations_90d"], 2)
        self.assertEqual(out["lens-x"]["median_90d_as_of"], self.TODAY)
        self.assertNotIn("lens-unknown", out)

    def test_state_does_not_move_last_seen_backward(self):
        prev = {"lens-x": {"name": "X", "category": "lens", "brand": "X", "mount": None,
                           "last_seen": "2026-10-24", "last_price": 200, "median_90d": 200,
                           "observations_90d": 1, "median_90d_as_of": "2026-10-24"}}
        state = {"a": {"mk": "lens-x", "ls": "2026-10-20", "p": [["2026-10-20", 10]]}}
        out = update_model_seen(prev, {}, state, self.TODAY)
        self.assertEqual((out["lens-x"]["last_seen"], out["lens-x"]["last_price"]), ("2026-10-24", 200))

    def test_keeps_day_90_and_drops_day_91(self):
        old = iso_minus(self.TODAY, 91)
        edge = iso_minus(self.TODAY, 90)
        prev = {
            "lens-old": {"name": "Old", "category": "lens", "brand": "Old", "mount": None,
                         "last_seen": old, "last_price": 40, "observations_90d": 1, "median_90d_as_of": old},
            "lens-edge": {"name": "Edge", "category": "lens", "brand": "Edge", "mount": None,
                          "last_seen": edge, "last_price": 41, "observations_90d": 1, "median_90d_as_of": edge},
        }
        out = update_model_seen(prev, {}, {}, self.TODAY)
        self.assertNotIn("lens-old", out)
        self.assertEqual(out["lens-edge"]["last_price"], 41)

    def test_listing_again_returns_the_page_to_today(self):
        prev = {"camera-canon-r5": {"name": "Canon EOS R5", "category": "camera", "brand": "Canon", "mount": "Canon RF",
                                    "last_seen": "2026-09-01", "last_price": 2500, "median_90d": 2600,
                                    "observations_90d": 2, "median_90d_as_of": "2026-09-01"}}
        out = update_model_seen(prev, {"camera-canon-r5": self._live(min_price=2700)}, {}, self.TODAY)
        self.assertEqual(out["camera-canon-r5"]["last_seen"], self.TODAY)
        self.assertEqual(out["camera-canon-r5"]["last_price"], 2700)

    def test_rejects_unsafe_keys_and_missing_names(self):
        prev = {
            "../etc": {"name": "Nope", "last_seen": "2026-10-20", "last_price": 10},
            "lens-ok": {"name": "   ", "last_seen": "2026-10-20", "last_price": 10},
            "Lens-Bad": {"name": "Bad", "last_seen": "2026-10-20", "last_price": 10},
        }
        models = {"bad key": {"name": "Bad", "min_price": True, "category": "lens"}}
        self.assertEqual(update_model_seen(prev, models, {}, self.TODAY), {})

    def test_new_price_is_copied_only_when_given(self):
        live = {"camera-canon-r5": self._live()}
        prices = {"camera-canon-r5": {"price": 4299, "url": "https://example.com/r5", "dealer": "The Camera Store"}}
        out = update_model_seen({}, live, {}, self.TODAY, new_prices=prices)
        self.assertEqual(out["camera-canon-r5"]["new_price"], 4299)
        self.assertEqual(out["camera-canon-r5"]["new_price_url"], "https://example.com/r5")
        bare = update_model_seen(out, live, {}, self.TODAY)
        self.assertNotIn("new_price", bare["camera-canon-r5"])


if __name__ == "__main__":
    unittest.main()
