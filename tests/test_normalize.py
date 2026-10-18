import unittest

from scraper.normalize import make_listing


def L(title, **kw):
    return make_listing("t", "Test", title, 100, "https://example.com", fetched_at="2026-01-01T00:00:00+00:00", **kw)


class NormalizeTests(unittest.TestCase):
    def test_lens_basic(self):
        x = L("Nikon NIKKOR Z 24-70mm f/4 S Used Lens")
        self.assertEqual((x["category"], x["brand"], x["mount"]), ("lens", "Nikon", "Nikon Z"))
        self.assertEqual(x["model_key"], "lens-nikon-nikon-z-24-70mm-f4-s")

    def test_third_party_mount(self):
        x = L("Sigma 35mm F1.4 DG HSM Art for Canon EF (EX+)")
        self.assertEqual((x["brand"], x["mount"], x["condition"]), ("Sigma", "Canon EF", "Excellent"))

    def test_downtown_shorthand(self):
        x = L("FUJI 16F1.4 R WR")
        self.assertEqual((x["category"], x["brand"], x["mount"]), ("lens", "Fujifilm", "Fujifilm X"))
        self.assertTrue(x["model_key"].endswith("16mm-f1_4"))

    def test_accessory_not_lens(self):
        self.assertEqual(L("Nikon Lens Hood HB-78 (For 70-200mm f2.8E FL ED VR)(EX+) used")["category"], "accessory")
        self.assertEqual(L("USAGE (8) - Canon BG-R10")["category"], "accessory")

    def test_conditions(self):
        self.assertEqual(L("USAGE (8) - Nikon AF-S 50mm f/1.8G")["condition"], "Good")
        self.assertEqual(L("Pentax-M 50mm F2 (BGN) Used Lens")["condition"], "Fair")
        self.assertEqual(L("Canon 70-200mm f4 L IS (LN-) RF used")["condition"], "Like New")
        self.assertEqual(L("Battery Grip Canon BG-R20 - *A+*")["condition"], "Like New")
        self.assertEqual(L("Nikon 20mm", condition_hint="Condition: Very Good")["condition"], "Good")

    def test_versions_split(self):
        a = L("Nikon AF Micro-Nikkor 105mm f/2.8D")["model_key"]
        b = L("Nikon AF-S VR Micro-Nikkor 105mm f/2.8G IF-ED")["model_key"]
        self.assertNotEqual(a, b)

    def test_cameras(self):
        self.assertEqual(L("Sony A7 III Body (EX)")["model_key"], "camera-sony-a7-iii")
        self.assertEqual(L("Canon EOS R6 Mark II Body")["model_key"], "camera-canon-r6-ii")
        self.assertEqual(L("Fujifilm X-T5 Body - *A*")["mount"], "Fujifilm X")


if __name__ == "__main__":
    unittest.main()
