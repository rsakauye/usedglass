"""Heuristic (AI-free) normalization: brand, mount, category, condition grade, model matching key."""
from __future__ import annotations

import hashlib
import html
import re

# ---------------------------------------------------------------- brand
BRAND_PATTERNS: list[tuple[str, str]] = [
    ("Canon", r"\bcanon\b|\bcanonet\b"),
    ("Nikon", r"\bnikon\b|\bnikkor\b|\bnikkormat\b"),
    ("Sony", r"\bsony\b|\bsel\s?\d|\bilce-?\d"),
    ("Fujifilm", r"\bfuji(film)?\b|\bfujinon\b|\bfujica\b|\binstax\b"),
    ("Panasonic", r"\bpanasonic\b|\blumix\b"),
    ("OM System", r"\bom system\b|\bom-?\d\b"),
    ("Olympus", r"\bolympus\b|\bzuiko\b|\bm\.zuiko\b"),
    ("Leica", r"\bleica\b|\bleitz\b|\bsummicron\b|\bsummilux\b|\belmarit\b"),
    ("Hasselblad", r"\bhasselblad\b"),
    ("Pentax", r"\bpentax\b|\btakumar\b|\basahi\b"),
    ("Ricoh", r"\bricoh\b"),
    ("Sigma", r"\bsigma\b"),
    ("Tamron", r"\btamron\b"),
    ("Tokina", r"\btokina\b"),
    ("Zeiss", r"\bzeiss\b|\bcontax\b"),
    ("Voigtlander", r"\bvoigtl(a|ä|ae)nder\b"),
    ("Samyang", r"\bsamyang\b|\brokinon\b"),
    ("Viltrox", r"\bviltrox\b"),
    ("Laowa", r"\blaowa\b|\bvenus optics\b"),
    ("TTArtisan", r"\bttartisans?\b"),
    ("7Artisans", r"\b7\s?artisans\b"),
    ("Minolta", r"\bminolta\b|\brokkor\b"),
    ("Konica", r"\bkonica\b|\bhexanon\b"),
    ("Mamiya", r"\bmamiya\b"),
    ("Bronica", r"\bbronica\b|\bzenza\b"),
    ("Rollei", r"\brollei(flex|cord)?\b"),
    ("Yashica", r"\byashica\b"),
    ("Kodak", r"\bkodak\b"),
    ("Polaroid", r"\bpolaroid\b"),
    ("DJI", r"\bdji\b"),
    ("GoPro", r"\bgopro\b"),
    ("Blackmagic", r"\bblackmagic\b|\bbmpcc\b"),
    ("Godox", r"\bgodox\b"),
    ("Profoto", r"\bprofoto\b"),
    ("Metz", r"\bmetz\b"),
    ("Nissin", r"\bnissin\b"),
    ("Manfrotto", r"\bmanfrotto\b"),
    ("Gitzo", r"\bgitzo\b"),
    ("Peak Design", r"\bpeak design\b"),
    ("Lowepro", r"\blowepro\b"),
    ("Think Tank", r"\bthink ?tank\b"),
    ("Vivitar", r"\bvivitar\b"),
    ("Soligor", r"\bsoligor\b"),
    ("Helios", r"\bhelios\b"),
    ("Industar", r"\bindustar\b"),
    ("Zenit", r"\bzenit\b"),
    ("Kenko", r"\bkenko\b"),
    ("Hoya", r"\bhoya\b"),
    ("B+W", r"\bb\+w\b"),
    ("Mitakon", r"\bmitakon\b|\bzhongyi\b"),
    ("Meike", r"\bmeike\b"),
    ("Yongnuo", r"\byongnuo\b"),
    ("Elinchrom", r"\belinchrom\b"),
    ("Broncolor", r"\bbroncolor\b"),
    ("Sekonic", r"\bsekonic\b"),
    ("Lomography", r"\blomo(graphy)?\b"),
    ("Contax", r"$^"),  # handled by Zeiss
]
FIRST_PARTY = {"Canon", "Nikon", "Sony", "Fujifilm", "Panasonic", "Olympus", "OM System", "Leica", "Pentax", "Hasselblad"}


def detect_brand(text: str, hint: str = "") -> str | None:
    t = f"{hint} {text}".lower()
    # third-party lens makers win over the mount brand ("Sigma 35mm for Canon EF")
    best = None
    best_pos = 10 ** 9
    for brand, rx in BRAND_PATTERNS:
        m = re.search(rx, t)
        if m:
            third = brand not in FIRST_PARTY
            pos = m.start() - (5000 if third else 0)
            if pos < best_pos:
                best, best_pos = brand, pos
    return best


# ---------------------------------------------------------------- category
ACCESSORY_RX = (r"\b(bg-?\w+|mb-?d?\d+|vg-?\w+|hdmi|xlr|power bank|battery pack|hood|cap|caps|filter|battery|batteries|charger|grip|strap|bag|case|backpack|tripod|monopod|head|"
                r"plate|cable|cord|remote|release|adapter|adaptor|bague|tube|tubes|extension|eyecup|viewfinder|finder|"
                r"loupe|screen|focusing screen|bellows|close-?up|diopter|bracket|mount adapter|card|reader|"
                r"pouch|cover|sunshade|step-?up|lens hood|pare-soleil|bouchon|chargeur|batterie|sac|courroie)\b")
FLASH_RX = r"\b(flash|speedlite|speedlight|strobe|softbox|light stand|monolight|monohead|led panel|ring light|trigger|transmitter|ttl|st-e\d\S*|\d{3}ex\S*|sb-?\d{3}|hvl-\S+)\b"
CAMERA_RX = r"\b(body|bo[iî]tier|camera|cam[eé]ra|dslr|slr|mirrorless|rangefinder|point\s?&\s?shoot|compact|camcorder)\b"
FOCAL_RX = r"(?<![\d.])(\d{1,4}(?:[-–]\d{1,4})?)\s?mm\b"
# Downtown Camera style shorthand: "16F1.4", "50-250F4.5-6.3", "7.5F3.5"
FOCAL_SHORT_RX = r"(?<![\w.])(\d{1,4}(?:\.\d)?(?:-\d{1,4})?)\s?f\s?/?(\d{1,2}(?:\.\d)?(?:-\d{1,2}(?:\.\d)?)?)\b"


def find_focal(t: str):
    """Return (focal, aperture_or_None, start) from a lowercase title."""
    m = re.search(FOCAL_RX, t)
    if m:
        return m.group(1).replace("–", "-"), None, m.start()
    m = re.search(FOCAL_SHORT_RX, t)
    if m and not re.match(r"\d{4}$", m.group(1)):
        return m.group(1), m.group(2), m.start()
    return None, None, -1
APERTURE_RX = r"(?:\bf|\bF|1:|ƒ)\s?/?\s?(\d{1,2}(?:\.\d)?)(?:\s?[-–]\s?(\d{1,2}(?:\.\d)?))?"
TELECONV_RX = r"\b(teleconverter|extender|tc-?\d|ef ?\d\.\dx|\d\.\dx)\b"


def detect_category(text: str, hint: str = "") -> str:
    t = f"{text} {hint}".lower()
    focal, _, fpos = find_focal(t)
    has_focal = focal is not None
    if re.search(TELECONV_RX, t):
        return "lens"
    if re.search(FLASH_RX, t):
        return "flash/lighting"
    am = re.search(ACCESSORY_RX, t)
    if am and (not has_focal or am.start() < fpos or not re.search(APERTURE_RX, t) and not re.search(FOCAL_SHORT_RX, t)):
        # "Lens Hood HB-78 (for 70-200mm f2.8)" -> accessory; "50mm f1.8 with hood" -> lens
        return "accessory"
    if has_focal or re.search(r"\blens\b|\bobjectif\b|\bnikkor\b|\bzuiko\b", t):
        if re.search(CAMERA_RX, t) and re.search(r"\b(kit|w/|with|avec)\b", t):
            return "camera"  # camera kit
        return "lens"
    if re.search(CAMERA_RX, t) or camera_model(text, detect_brand(text)):
        return "camera"
    return "accessory"


# ---------------------------------------------------------------- mount
LENS_MOUNT_RULES: list[tuple[str, str]] = [
    ("Canon RF", r"\brf-?s?\s?\d|\brf\b(?! ?used)|\brf(?= used)|\bcanon rf\b|\brf[- ]mount|\bfor canon rf\b|\bpour canon rf\b"),
    ("Canon EF-M", r"\bef-m\b"),
    ("Canon EF", r"\bef-?s?\s?\d|\bef-?s?\b|\bcanon ef\b|\bef[- ]mount|\bfor canon\b(?! rf)|\beos\b(?!\s?r)"),
    ("Canon FD", r"\bfdn?\b|\bnfd\b|\bfl\s?\d"),
    ("Nikon Z", r"\bnikkor z\b|\bz\s?(dx|mc)\b|\bnikon z\b|\bz[- ]mount|\bfor nikon z\b|\bpour nikon z\b|\bz \d{2,3}mm|\bnikkor z\d"),
    ("Nikon F", r"\baf-?[spdi]\b|\bai-?s?\b|\bnikon f\b|\bf[- ]mount|\bfor nikon\b(?! z)|\bpour nikon\b(?! z)|\bnikkor\b"),
    ("Sony E", r"\bfe\s?\d|\bsel\s?\d|\bsony e\b|\be[- ]mount|\bfor sony\b(?! a)|\bpour sony\b|\bsony fe\b|\bdi iii\b|\bdn\b"),
    ("Sony A", r"\bsal\s?\d|\ba[- ]mount\b|\bminolta af\b|\bmaxxum\b"),
    ("Fujifilm G", r"\bgf\s?\d|\bg[- ]mount\b|\bfor gfx\b|\bgfx\b"),
    ("Fujifilm X", r"\bxf\s?\d|\bxc\s?\d|\bx[- ]mount|\bfor fuji(film)? x\b|\bfuji(film)? x\b|\bfor fuji(film)?\b"),
    ("Micro Four Thirds", r"\bm4/3\b|\bmft\b|\bmicro (four|4)[- ]thirds\b|\bm\.?\s?zuiko\b|\blumix g\b|\bleica dg\b|\bm43\b"),
    ("Four Thirds", r"\bfour thirds\b|\bzuiko digital\b"),
    ("L-Mount", r"\bl[- ]mount\b|\bmonture l\b|\blumix s\b|\bfor l\b|\bleica sl\b|\bleica tl?\b"),
    ("Leica M", r"\bleica m\b|\bm[- ]mount\b|\bvm\b|\bzm\b|\bm39\b|\bltm\b"),
    ("Leica R", r"\bleica r\b|\br[- ]mount\b"),
    ("Pentax K", r"\bpentax-?[ma]\b|\bp/k\b|\bpentax k\b|\bk[- ]mount\b|\bpk\b|\bsmc\b|\bda\s?\d|\bfa\s?\d|\bd fa\b"),
    ("M42", r"\bm42\b|\btakumar\b"),
    ("Minolta MD", r"\bminolta (md|mc)\b|\bmd rokkor\b|\bmc rokkor\b|\bsr[- ]mount\b"),
    ("Hasselblad V", r"\bhasselblad v\b|\b(cf|cfi|cfe)\b"),
    ("Hasselblad XCD", r"\bxcd\b"),
]
CAMERA_MOUNT_RULES: list[tuple[str, str, str]] = [
    ("Canon", r"\b(eos\s?)?r(1|3|5|5c|6|7|8|10|50|50v|100|p)\b|\beos r\b", "Canon RF"),
    ("Canon", r"\beos\s?m\d*\b|\bm(50|6|100|200)\b", "Canon EF-M"),
    ("Canon", r"\b(\d{1,3}d|rebel|t\d+i?|sl\d|1d[sx]?|5ds?r?)\b", "Canon EF"),
    ("Nikon", r"\bz\s?(5|6|7|8|9|f|fc|30|50|6ii|7ii)\b|\bzf\b|\bzfc\b", "Nikon Z"),
    ("Nikon", r"\bd\d{1,4}[a-z]?\b|\bf\d\b|\bfm\d?\b|\bfe\d?\b|\bf100\b", "Nikon F"),
    ("Sony", r"\b(a|α|ilce-?)(7|9|1|6\d{3}|7c|7r|7s|7cr)\w*\b|\bzv-?e\d+\b|\bfx(3|30|6)\b|\bnex", "Sony E"),
    ("Fujifilm", r"\bgfx\b", "Fujifilm G"),
    ("Fujifilm", r"\bx-?(t|s|e|h|pro|a|m)\s?\d", "Fujifilm X"),
    ("Panasonic", r"\blumix s\d|\bs(1|5)\w*\b", "L-Mount"),
    ("Panasonic", r"\b(gh|g|gx|gf)\s?\d", "Micro Four Thirds"),
    ("Olympus", r"\b(e-?m\d|pen|om-?d)\b", "Micro Four Thirds"),
    ("OM System", r"\bom-?\d\b|\bom-5\b", "Micro Four Thirds"),
    ("Leica", r"\bleica m\d*\b|\bm(6|7|8|9|10|11)\b", "Leica M"),
    ("Leica", r"\bsl\d?\b|\bcl\b|\btl2?\b", "L-Mount"),
    ("Pentax", r"\bk-?\d+\b|\bkp\b|\bk-?3\b", "Pentax K"),
]


def detect_mount(text: str, brand: str | None, category: str, hint: str = "") -> str | None:
    t = f"{text} {hint}".lower()
    if category == "camera":
        for b, rx, mount in CAMERA_MOUNT_RULES:
            if (brand == b or brand is None) and re.search(rx, t):
                return mount
        return None
    for mount, rx in LENS_MOUNT_RULES:
        if re.search(rx, t):
            # guard brand-specific shorthand against mismatched brands
            if mount.startswith("Canon") and brand in {"Nikon", "Sony", "Fujifilm", "Pentax", "Olympus", "Leica"}:
                continue
            if mount.startswith("Nikon") and brand in {"Canon", "Sony", "Fujifilm", "Pentax", "Olympus", "Leica"}:
                continue
            if mount == "Sony E" and brand in {"Canon", "Nikon", "Fujifilm", "Pentax", "Olympus"} and "sony" not in t:
                continue
            return mount
    # brand default for first-party lenses where shorthand is absent
    if category == "lens" and brand == "Fujifilm" and "instax" not in t:
        return "Fujifilm X"
    if category == "lens" and brand == "Olympus" and "om-" not in t:
        return "Micro Four Thirds" if "digital" not in t else "Four Thirds"
    return None


# ---------------------------------------------------------------- condition
GRADES = ["Like New", "Excellent", "Good", "Fair", "As Is"]
CONDITION_RULES: list[tuple[str, str]] = [
    ("As Is", r"\bas[- ]is\b|\bfor parts\b|\bparts only\b|\bdefective\b|\bnot working\b|\bfungus\b|\bpour pi[eè]ces\b"),
    ("Like New", r"\(ln-?\)|\bln-?\b|\blike new\b|\bmint\b|\*a\+\*|\ba\+|\bopen[- ]box\b|\bdemo\b|\bnew in box\b|\bcomme neuf\b|\b(9\.5|10)\s?/\s?10\b|\b(10|9\+)\b(?=\s*\)|\s*$)"),
    ("Excellent", r"\(ex\+?\)|\bex\+?\b|\bexc\b|\bexcellent\b|\*a\*|\b9\s?/\s?10\b|\bvery good\b|\btr[eè]s bon\b"),
    ("Good", r"\bgood\b|\bgd\b|\*b\+?\*|\b8\s?/\s?10\b|\bbon [ée]tat\b|\bvg\b"),
    ("Fair", r"\(bgn\)|\bbgn\b|\bbargain\b|\bfair\b|\*c\*|\b[5-7]\s?/\s?10\b|\bwell used\b|\bheavy wear\b|\bud\b"),
]
GOSSELIN_RX = r"usag[ée]e?\s*\((\d{1,2})\)"


def detect_condition(text: str, hint: str = "") -> str | None:
    t = f"{text} {hint}".lower()
    m = re.search(GOSSELIN_RX, t)  # Gosselin "USAGE (8) - ..." numeric 1-10 grade
    if m:
        n = int(m.group(1))
        return "Like New" if n >= 10 else "Excellent" if n == 9 else "Good" if n == 8 else "Fair" if n >= 5 else "As Is"
    m = re.search(r"condition\s*:\s*(a\+|a|b\+|b|c|[\d.]+\+?|[a-z ]{3,12})", t)  # Camtec / Beau descriptions
    if m:
        g = m.group(1).strip()
        mapping = {"a+": "Like New", "a": "Excellent", "b+": "Good", "b": "Good", "c": "Fair"}
        for word, grade in [("like new", "Like New"), ("mint", "Like New"), ("excellent", "Excellent"),
                            ("very good", "Good"), ("good", "Good"), ("fair", "Fair"), ("poor", "Fair"),
                            ("as is", "As Is"), ("parts", "As Is")]:
            if g.startswith(word):
                return grade
        if g in mapping:
            return mapping[g]
        try:
            n = float(g.rstrip("+"))
            if n > 10:
                n = n / 10
            return "Like New" if n >= 9.5 else "Excellent" if n >= 9 else "Good" if n >= 8 else "Fair" if n >= 5 else "As Is"
        except ValueError:
            pass
    for grade, rx in CONDITION_RULES:
        if re.search(rx, t):
            return grade
    return None


# ---------------------------------------------------------------- model matching
DESIGNATORS = [
    (r"\bmark\s?(ii|iii|iv|2|3|4)\b|\bmk\s?(ii|iii|iv|2|3|4)\b|\b(ii|iii|iv)\b", "ver"),
    (r"\bgm\s?(ii|2)?\b|g master", "GM"),
    (r"(?<=\d)l\b|\bl\b(?= ?(is|usm|ii|iii)\b)|\bl-series\b|\b\d+(\.\d)?l\b", "L"),
    (r"(?<![-\w])s\b(?!-)", "S"),
    (r"\bart\b", "ART"), (r"\bcontemporary\b|\b\| ?c\b", "C"), (r"\bsports?\b(?! photo)", "SPORT"),
    (r"\bmacro\b|\bmicro\b(?! four)", "MACRO"), (r"\bfisheye\b|\bfish-?eye\b", "FISHEYE"),
    (r"\btilt|\bshift\b|\bts-e\b|\bpc-e\b", "TS"), (r"\bdx\b", "DX"), (r"\bpro\b", "PRO"),
    (r"\blimited\b|\bltd\b", "LTD"), (r"\bplena\b", "PLENA"), (r"\bnoct\b", "NOCT"),
    (r"\bstm\b", "STM"), (r"\bvcm\b", "VCM"),
    (r"\bvr\b|\bis\b|\boss\b|\bos\b|\bvc\b|\bois\b", "STAB"),
    (r"\baf-?s\b", "AFS"), (r"\baf-?p\b", "AFP"), (r"\bai-?s\b|\bais\b", "AIS"),
    (r"\d(?:\.\d)?\s?d\b|\baf-?d\b", "AFD"), (r"\bfl\b", "FL"), (r"\blm\b", "LM"),
]
BRAND_ONLY_TAGS = {"AFS": "Nikon", "AFP": "Nikon", "AIS": "Nikon", "AFD": "Nikon", "FL": "Nikon", "LM": "Fujifilm"}
VER_MAP = {"2": "II", "3": "III", "4": "IV", "ii": "II", "iii": "III", "iv": "IV"}


def _num(s: str) -> str:
    return s.rstrip("0").rstrip(".") if "." in s else s


def lens_key(text: str, brand: str | None, mount: str | None) -> tuple[str | None, str | None]:
    t = html.unescape(text).lower().replace("–", "-").replace(",", ".")
    t = re.sub(r"\b(vr|is|gm)(ii|iii)\b", r"\1 \2", t)  # Downtown shorthand "VRII"
    focal, ap_short, fpos = find_focal(t)
    if not focal or not brand:
        return None, None
    ap = None
    if ap_short:
        ap = "-".join(_num(a) for a in ap_short.split("-"))
    else:
        am = re.search(APERTURE_RX, t[max(fpos - 20, 0):] + " ")
        if am:
            ap = _num(am.group(1)) + ("-" + _num(am.group(2)) if am.group(2) else "")
    if ap and "-" in ap and "-" not in focal:
        ap = ap.split("-")[0]
    tags = []
    for rx, tag in DESIGNATORS:
        m = re.search(rx, t)
        if m and tag:
            if tag == "ver":
                v = next((g for g in m.groups() if g), None)
                tags.append(VER_MAP.get(v, v.upper()) if v else "")
            elif tag == "S" and mount != "Nikon Z":
                continue
            elif tag == "L" and brand != "Canon":
                continue
            elif tag == "GM" and brand != "Sony":
                continue
            elif tag in {"ART", "C", "SPORT"} and brand != "Sigma":
                continue
            elif tag in BRAND_ONLY_TAGS and BRAND_ONLY_TAGS[tag] != brand:
                continue
            else:
                tags.append(tag)
    tags = sorted(set(x for x in tags if x))
    mount_part = mount or ("?" if brand not in FIRST_PARTY else "")
    key = "|".join(["lens", brand, mount_part, f"{focal}mm", f"f{ap}" if ap else "f?", ".".join(tags)])
    name = f"{brand} {focal}mm" + (f" f/{ap}" if ap else "") + (" " + " ".join(tags) if tags else "") + (f" ({mount})" if mount else "")
    return slugify(key), name


def camera_model(text: str, brand: str | None) -> tuple[str, str] | None:
    t = html.unescape(text).lower()
    pats = {
        "Canon": r"(?<![-/\w])(?:eos\s?)?(r\d{1,3}[a-z]?|(?<=eos )r|rp|\d{1,4}d[sxr]{0,2}|rebel\s?[a-z]{1,2}\d*i?|m\d{0,3}|g\d{1,2}x?|powershot\s?\w+)"
                 r"(?:\s?(?:mark|mk|m)\s?(ii|iii|iv|2|3|4))?\b",
        "Nikon": r"\b(z\s?\d{1,2}|zf|zfc|z\s?fc|d\d{1,4}[a-z]?|f\d|fm\d?|fe\d?|coolpix\s?\w+)\s?(ii|iii)?\b",
        "Sony": r"\b(?:a|α|ilce-?)\s?(7|9|1|7c|7r|7s|7cr|6\d{3}|99|77|68)\s?(?:(ii|iii|iv|v)|m(\d))?\b|\b(rx\d{1,3})\s?(?:(ii|iii|iv|v|vi|vii)|m(\d))?\b|\b(zv-?e\d{1,2}|fx\d{1,2})\b",
        "Fujifilm": r"\b(x-?(?:t|s|e|h|pro|a|m)\s?\d{1,3}[a-z]?|x100\s?[a-z]{0,2}|gfx\s?\d{2,3}[a-z]{0,2}|x-?\d{2}|xf\d{2})\s?(ii)?\b",
        "Panasonic": r"\b(?:dc-|dmc-)?(gh\d[a-z]?|g\d{1,3}|gx\d{1,3}|s\d[a-z]{0,2}|lx\d{1,3})\s?(ii)?\b",
        "Olympus": r"\b(e-?m\d{1,2})\s?(?:mark|mk)?\s?(ii|iii|iv)?\b|\b(om-?\d|pen-?f|e-?p\d)\b",
        "OM System": r"\b(om-?\d)\s?(ii)?\b",
        "Leica": r"\b(m\d{1,2}[a-z-]*|q\d?|sl\d?|cl|tl\d?)\b",
        "Pentax": r"\b(k-?\d{1,4}[a-z]{0,2}|kp|k1000|me super|spotmatic|67)\s?(ii)?\b",
        "Ricoh": r"\b(gr\s?(?:iii|iv|ii)x?|gr\d?)\b",
    }
    for b, rx in pats.items():
        if brand is not None and brand != b:
            continue
        m = re.search(rx, t)
        if m:
            groups = [g for g in m.groups() if g]
            if not groups:
                continue
            model = re.sub(r"[\s-]+", "", groups[0]).upper()
            if b == "Sony" and re.match(r"^\d", model):
                model = "A" + model
            ver = groups[1] if len(groups) > 1 else ""
            ver = VER_MAP.get(ver, ver.upper()) if ver else ""
            if ver.isdigit():
                ver = {"2": "II", "3": "III", "4": "IV", "5": "V"}.get(ver, ver)
            return model, ver
    return None


def camera_key(text: str, brand: str | None) -> tuple[str | None, str | None]:
    if not brand:
        return None, None
    cm = camera_model(text, brand)
    if not cm:
        return None, None
    model, ver = cm
    key = "|".join(["camera", brand, model, ver])
    return slugify(key), f"{brand} {model}{(' ' + ver) if ver else ''}"


def slugify(s: str) -> str:
    s = s.lower().replace("|", "-").replace(".", "_").replace("/", "-")
    s = re.sub(r"[^a-z0-9_-]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


# ---------------------------------------------------------------- public API
def clean_title(t: str) -> str:
    t = html.unescape(re.sub(r"\s+", " ", t or "")).strip()
    t = re.sub(r"\b(\w+) \1\b", r"\1", t, flags=re.I)  # "Nikon NIKON Z" -> "Nikon Z"
    return t


def parse_price(p) -> float | None:
    if p is None or p == "":
        return None
    try:
        v = float(re.sub(r"[^\d.]", "", str(p)))
        return round(v, 2) if v > 0 else None
    except ValueError:
        return None


def make_listing(dealer_id: str, dealer: str, title: str, price, url: str, *, sku: str | None = None,
                 in_stock: bool = True, condition_hint: str = "", category_hint: str = "", brand_hint: str = "",
                 fetched_at: str, source: str = "dealer", image: str | None = None, location: str | None = None) -> dict:
    title = clean_title(title)
    brand = detect_brand(title, brand_hint)
    category = detect_category(title, category_hint)
    mount = detect_mount(title, brand, category, category_hint)
    condition = detect_condition(title, condition_hint)
    if category == "lens":
        model_key, model_name = lens_key(title, brand, mount)
    elif category == "camera":
        model_key, model_name = camera_key(title, brand)
    else:
        model_key, model_name = None, None
    ident = sku or url or title
    lid = f"{dealer_id}-" + hashlib.sha1(f"{ident}|{title if not sku else ''}".encode()).hexdigest()[:10]
    return {
        "id": lid, "dealer_id": dealer_id, "dealer": dealer, "source": source, "title": title,
        "brand": brand, "mount": mount, "category": category, "condition": condition,
        "model_key": model_key, "model_name": model_name, "price_cad": parse_price(price), "url": url,
        "in_stock": bool(in_stock), "image": image, "location": location, "fetched_at": fetched_at,
    }
