import unittest

from scraper.normalize import display_title, make_listing


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

    def test_new_mounts(self):
        cases = {
            "TAMRON 28-75F2.8 XR DI NIK": "Nikon F",
            "SIGMA 30F1.4 DC \"C\" FUJI XF": "Fujifilm X",
            "USAGE (8) - NIKON 50mm f/2.8 MC Monture Z": "Nikon Z",
            "Olympus OM G Zuiko Auto N 28mm F3.5 Used Lens": "Olympus OM",
            "Tamron 90mm F2.5 (BGN) Used Lens for Mamiya 645 Mount": "Mamiya 645",
            "Used Pentax 67 Macro 135mm f4": "Pentax 67",
            "Tokina RMC 80-200mm f4 (BGN) Y/C used": "Contax/Yashica",
            "Used Fujinon A 240mm f9 lens on 4×4 Deardorff board": "Large Format",
            "Pentax-M 50mm F2 (BGN) Used Lens": "Pentax K",
            "Used Sony Sonnar E 24mm f/1.8": "Sony E",
            "Sony A 16mm F2.8 SAM Used Fisheye Lens": "Sony A",
            "Leica Vario-Elmarit 24-70mm f2.8 ASPH. *USED": "L-Mount",
            "Leica Summaron 35mm f2.8 Goggles *USED": "Leica M",
        }
        for title, mount in cases.items():
            self.assertEqual(L(title)["mount"], mount, title)

    def test_camera_mounts_and_kits(self):
        self.assertEqual(L("Leica Q3 *USED")["mount"], "Fixed Lens")
        self.assertEqual(L("Nikon FTn W/55F3.5 MICRO BK")["mount"], "Nikon F")
        x = L("Nikon Z30 + 16-50mm f3.5-6.3 DX VR (SC 300) used")
        self.assertEqual((x["category"], x["mount"]), ("camera", "Nikon Z"))
        x = L("Sony A7 III with Sigma 35mm f1.4 Art")
        self.assertEqual((x["category"], x["brand"]), ("camera", "Sony"))
        self.assertEqual(L("MINOLTA 7000 W/35-70F3.5-4.5")["mount"], "Sony A")
        self.assertIsNone(L("MoviePix HD Video Camera - Used")["mount"])

    def test_more_brands_and_hints(self):
        self.assertEqual(L("Used Hensel 40 Degree grid")["brand"], "Hensel")
        self.assertEqual(L("Neewer TT560 Flash (Canon)(EX) used")["brand"], "Neewer")
        self.assertEqual(L("Plus III Transceivers", brand_hint="Pocketwizard")["brand"], "PocketWizard")
        self.assertEqual(L("Some Widget 3000", brand_hint="Acme Optics")["brand"], "Acme Optics")
        self.assertIsNone(L("Some Widget 3000", brand_hint="Other")["brand"])
        self.assertEqual(L("Nikon D3200", mount_hint="Nikon F")["mount"], "Nikon F")

    def test_more_conditions(self):
        self.assertEqual(L("Nikon AF-S 70-200mm f/2.8G ED VR II Lens — Near Mint")["condition"], "Like New")
        self.assertEqual(L("Canon EF 24-70mm f/2.8L USM Lens - Excellent Plus")["condition"], "Excellent")
        self.assertEqual(L("Canon EF 50mm f/1.8 STM - Very Good")["condition"], "Good")
        self.assertEqual(L("PENTAX 50F1.4 PK-A MINTY")["condition"], "Like New")
        self.assertEqual(L("USAGE (N) - Hasselblad XCD 75mm f/3.4")["condition"], "Like New")
        self.assertIsNone(L("Sigma 70-200mm F2.8 EX DG HSM for Canon")["condition"])
        self.assertEqual(L("Nikon D3200", condition_hint="Some cosmetic wear, scuffs on the screen")["condition"], "Good")


class DisplayTitleTests(unittest.TestCase):
    def test_gosselin_prefix_and_pour(self):
        x = make_listing("gosselin", "Gosselin Photo", "USAGE (7) - Image 28mm f/2.8 pour Canon FD", "99", "u",
                         sku="1", fetched_at="t")
        self.assertEqual(x["title"], "Image 28mm f/2.8 for Canon FD")
        self.assertEqual(x["title_raw"], "USAGE (7) - Image 28mm f/2.8 pour Canon FD")
        self.assertEqual(x["condition"], "Fair")  # Gosselin grade 7 = 70-79% of original condition
        self.assertEqual(display_title("USAGE (8) - Takumar 135mm pour monture M42"), "Takumar 135mm for M42 mount")
        self.assertEqual(display_title("USAGE (8) - boule de crystal pour photographie"), "boule de crystal pour photographie")


if __name__ == "__main__":
    unittest.main()
