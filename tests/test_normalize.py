import unittest

from scraper.normalize import display_title, explicit_mount, make_listing


def L(title, **kw):
    return make_listing("t", "Test", title, 100, "https://example.com", fetched_at="2026-01-01T00:00:00+00:00", **kw)


class NormalizeTests(unittest.TestCase):
    def test_glued_focal_is_lens_not_body(self):
        x = L("Fujifilm XF16-55mmF2.8 R LM WR")
        self.assertEqual(x["category"], "lens")
        self.assertEqual(x["model_key"], "lens-fujifilm-fujifilm-x-16-55mm-f2_8-lm")
        self.assertEqual(L("Fujifilm Open Box FUJINON XF18-135mmF3.5-5.6 R LM OIS WR")["category"], "lens")

    def test_part_number_accessories_not_bodies(self):
        for t in ("Fujifilm BLC-XT10", "Fujifilm MHG-GFX S Metal Handgrip for GFX 100S - *A+*", "Nikon MB-N10 For Nikon Z6 and Z7 - *A*"):
            self.assertEqual(L(t)["category"], "accessory", t)
            self.assertIsNone(L(t)["model_key"], t)
        x = L("FUJI X-T10 W/16-50 SILVER")
        self.assertEqual((x["category"], x["model_key"]), ("camera", "camera-fujifilm-xt10"))

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


    def test_camera_kits_and_film_format(self):
        for t in ("Canon Open Box EOS R100 Mirrorless Camera 18-45mm Lens", "Used Nikon F55 w/ 28-80mm f3.5",
                  "Used Linhof Technika w/ Xenar 105mm f3.5", "Pentax ES 35mm Film SLR Camera Body (AS IS - Parts) Used",
                  "Canon Rebel Ti Used 35mm SLR"):
            self.assertEqual(L(t)["category"], "camera", t)
        self.assertTrue(L("NIKON FE2 W/50F1.8 Ai NIKKOR").get("bundle"))
        self.assertTrue(L("Used Nikon F55 w/ 28-80mm f3.5").get("bundle"))
        self.assertFalse(L("Nikon F2AS 35mm Film SLR Camera Body (BGN) Used").get("bundle"))
        self.assertNotEqual(L("Used Nikon F55 w/ 28-80mm f3.5")["model_key"], "camera-nikon-f3")  # f3.5 is an aperture
        self.assertIsNone(L("Canon TX 35mm Film SLR Camera with 50mm F1.8 Lens - Used")["model_key"])
        for t in ("Nikon BR-2 reversing ring with 52mm thread.", "Schneider B+W 138mm UV-410 Haze", "Used Slr Magic Cine 18mm f/2.8"):
            self.assertNotEqual(L(t)["category"], "camera", t)
        for t in ("Used Sigma APO 70-200mm f/2.8 II w/ 2X Tele converter", "Nikon TC-14E III 1.4X F-mount Teleconverter"):
            self.assertEqual(L(t)["category"], "lens", t)

    def test_accessories_that_mention_a_focal_or_body(self):
        for t in ("Nikon Focusing Screens for F3", "Nikon 22mm Eyepieces", "Used Nisi 150mm holder system for Sigma 14mm f1.8 lens",
                  "Kodak Carousel 35mm Slide Trays", "Canon C-8 Tele Converter 1.6X (48mm)", "The ExpoDisc (67mm)",
                  "Nikon HN-12 lens hoods", "Minolta clip-on lens hoods", "Mamiya Auto-Ext Ring No.2", "Used 35mm stainless steel film reel",
                  "Used Filters - 62mm Assorted - From $10", "Fotga M42-NEX/Sony E Lens Adapater - Used"):
            self.assertEqual(L(t)["category"], "accessory", t)
            self.assertIsNone(L(t)["model_key"], t)

    def test_overrides_file_entries_are_well_formed(self):
        from scraper.normalize import listing_overrides
        o = listing_overrides()
        self.assertTrue(o)
        for lid, v in o.items():
            self.assertLessEqual(set(v), {"category", "model_key", "bundle", "note"}, lid)
            self.assertIn(v.get("category", "lens"), {"lens", "camera", "accessory", "flash/lighting"}, lid)


class DisplayTitleTests(unittest.TestCase):
    def test_gosselin_prefix_and_pour(self):
        x = make_listing("gosselin", "Gosselin Photo", "USAGE (7) - Image 28mm f/2.8 pour Canon FD", "99", "u",
                         sku="1", fetched_at="t")
        self.assertEqual(x["title"], "Image 28mm f/2.8 for Canon FD")
        self.assertEqual(x["title_raw"], "USAGE (7) - Image 28mm f/2.8 pour Canon FD")
        self.assertEqual(x["condition"], "Fair")  # Gosselin grade 7 = 70-79% of original condition
        self.assertEqual(display_title("USAGE (8) - Takumar 135mm pour monture M42"), "Takumar 135mm for M42 mount")
        self.assertEqual(display_title("USAGE (8) - boule de crystal pour photographie"), "boule de crystal pour photographie")


class VariantAndMountTests(unittest.TestCase):
    """Real Oct 20, 2026 dealer titles. First drafted by qwen2.5-coder, reviewed and corrected by hand."""

    def test_suffix_variant_beats_base_model(self):
        cases = [
            ("Canon EOS R50 V with RF-S 14-30mm F4-6.3 IS STM PZ \\Bonus Battery OPEN BOX", "camera-canon-r50-v"),
            ("OM System Open Box OM-1 Mark II Mirrorless Camera Body", "camera-om-system-om1-ii"),
            ("Canon EOS R5 II (Body) - *A*", "camera-canon-r5-ii"),
            ("NIKON Z6 MK2 >112K", "camera-nikon-z6-ii"),
            ("Canon 5D III Used DSLR Camera", "camera-canon-5d-iii"),
            ("Canon 6D II DSLR Camera Body - Used", "camera-canon-6d-ii"),
            ("Fujifilm X-T30 III Used Mirrorless Camera Body", "camera-fujifilm-xt30-iii"),
            ("Pentax K-1 Mark II body", "camera-pentax-k1-ii"),
            ("Canon EOS 5D Mark IV", "camera-canon-5d-iv"),
        ]
        for title, key in cases:
            with self.subTest(title=title):
                x = L(title)
                self.assertEqual((x["category"], x["model_key"]), ("camera", key), title)

    def test_kit_lens_version_does_not_attach_to_body(self):
        cases = [
            ("Canon EOS Rebel T3 + 18-55mm F3.5-5.6 III (B-EX, L-BGN) Used", "camera-canon-rebelt3"),
            ("Nikon D3300 + 18-55mm f3.3-5.6 VR II (EX+) used", "camera-nikon-d3300"),
            ("Canon EOS R100 Mirrorless Camera 18-45mm Lens OPEN BOX", "camera-canon-r100"),
        ]
        for title, key in cases:
            with self.subTest(title=title):
                self.assertEqual(L(title)["model_key"], key, title)

    def test_stated_mount_beats_marker_guess(self):
        cases = [
            ("Tamron Demo 18-300mm f/3.5-6.3 Di III-A VC VXD FUJI X", "Fujifilm X"),
            ("Sigma 16mm F1.4 DC DN (EX+) Used Lens For Fujifilm X Mount", "Fujifilm X"),
            ("Sigma Open Box 24-70mm f2.8 DG DN II Art Lens L mount", "L-Mount"),
            ("SIGMA 60F2.8 DN M4/3", "Micro Four Thirds"),
            ("USAGE (8) - Sigma 30mm f/1.4 DC DN Contemporary pour Micro 4/3", "Micro Four Thirds"),
            ("Sony FE 28-135mm f4 SSM PZ *Used", "Sony E"),
            ("Sigma 18-50mm F2.8 DC DN Contemporary Sony E", "Sony E"),
            ("Tamron 28-75mm F2.8 Di III RXD", "Sony E"),  # no mount stated: the Di III marker still decides
        ]
        for title, mount in cases:
            with self.subTest(title=title):
                x = L(title)
                self.assertEqual((x["category"], x["mount"]), ("lens", mount), title)

    def test_micro_four_thirds_is_not_macro(self):
        self.assertNotIn("macro", L("USAGE (8) - Sigma 16mm f/1.4 DC DN micro 4/3")["model_key"])
        self.assertIn("macro", L("Nikon AF Micro-Nikkor 60mm f/2.8D")["model_key"])

    def test_explicit_mount_needs_exactly_one(self):
        self.assertIsNone(explicit_mount("Metabones Canon EF to Sony E-mount adapter"))
        self.assertEqual(explicit_mount("Viltrox 23mm f/1.4 for Nikon Z"), "Nikon Z")
        self.assertIsNone(explicit_mount("Fujifilm X-T3 body"))
        self.assertIsNone(explicit_mount("Sigma 35mm f/1.4 DG HSM Art"))


def load_tests(loader, tests, pattern):
    # tests/test_builders.py rides along so the existing Actions step runs it too
    from tests import test_builders
    tests.addTests(loader.loadTestsFromModule(test_builders))
    return tests


if __name__ == "__main__":
    unittest.main()
