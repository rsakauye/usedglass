"""Heuristic (AI-free) normalization: brand, mount, category, condition grade, model matching key."""
from __future__ import annotations

import hashlib
import html
import re

# ---------------------------------------------------------------- brand
# (display name, regex). Order only matters for ties at the same position.
BRAND_PATTERNS: list[tuple[str, str]] = [
    ("Canon", r"\bcanon\b|\bcanonet\b"),
    ("Nikon", r"\bnikon\b|\bnikkor\b|\bnikkormat\b"),
    ("Sony", r"\bsony\b|\bsel\s?\d|\bilce-?\d"),
    ("Fujifilm", r"\bfuji(film)?\b|\bfujinon\b|\bfujica\b|\binstax\b"),
    ("Panasonic", r"\bpanasonic\b|\blumix\b"),
    ("OM System", r"\bom system\b|\bom-?\d\b(?! ?(mount|zuiko))"),
    ("Olympus", r"\bolympus\b|\bzuiko\b|\bm\.zuiko\b"),
    ("Leica", r"\bleica\b|\bleitz\b|\bsummicron\b|\bsummilux\b|\belmarit\b|\bsummaron\b|\bnoctilux\b"),
    ("Hasselblad", r"\bhasselblad\b|\bxpan\b"),
    ("Pentax", r"\bpentax\b|\btakumar\b|\basahi\b"),
    ("Ricoh", r"\bricoh\b"),
    ("Sigma", r"\bsigma\b"),
    ("Tamron", r"\btamron\b"),
    ("Tokina", r"\btokina\b"),
    ("Contax", r"\bcontax\b"),
    ("Zeiss", r"\bzeiss\b|\bbatis\b|\bloxia\b|\botus\b|\bmilvus\b|\btouit\b"),
    ("Voigtlander", r"\bvoigtl(a|ä|ae)nder\b|\bnokton\b|\bheliar\b|\bcolor-skopar\b|\bultron\b"),
    ("Samyang", r"\bsamyang\b|\brokinon\b"),
    ("Viltrox", r"\bviltrox\b"),
    ("Laowa", r"\blaowa\b|\bvenus optics\b"),
    ("TTArtisan", r"\btt ?artisans?\b|\btt artisa\b"),
    ("7Artisans", r"\b7\s?artisans\b"),
    ("Thypoch", r"\bthypoch\b"),
    ("Artizlab", r"\bartizlab\b"),
    ("Sirui", r"\bsirui\b"),
    ("Irix", r"\birix\b"),
    ("Lensbaby", r"\blensbaby\b"),
    ("Schneider", r"\bschneider\b|\bcurtagon\b|\bsymmar\b|\bxenar\b|\bcomponon\b|\bangulon\b"),
    ("Rodenstock", r"\brodenstock\b|\bsironar\b|\brodagon\b"),
    ("Minolta", r"\bminolta\b|\brokkor\b|\bmaxxum\b|\bdynax\b"),
    ("Konica", r"\bkonica\b|\bhexanon\b|\bhexar\b"),
    ("Mamiya", r"\bmamiya\b"),
    ("Bronica", r"\bbronica\b|\bzenza\b|\bzenzanon\b"),
    ("Rollei", r"\brollei(flex|cord)?\b"),
    ("Yashica", r"\byashica\b"),
    ("Kodak", r"\bkodak\b"),
    ("Polaroid", r"\bpolaroid\b"),
    ("Minox", r"\bminox\b"),
    ("Praktica", r"\bpraktica\b|\bpentacon\b"),
    ("Exakta", r"\bexakta\b|\bihagee\b"),
    ("Topcon", r"\btopcon\b"),
    ("Miranda", r"\bmiranda\b"),
    ("Chinon", r"\bchinon\b"),
    ("Cosina", r"\bcosina\b"),
    ("Petri", r"\bpetri\b"),
    ("Agfa", r"\bagfa\b"),
    ("Graflex", r"\bgraflex\b|\bspeed graphic\b"),
    ("Linhof", r"\blinhof\b"),
    ("Sinar", r"\bsinar\b"),
    ("Toyo", r"\btoyo\b"),
    ("Wista", r"\bwista\b"),
    ("Holga", r"\bholga\b"),
    ("FED", r"\bfed-?\d\w*\b"),
    ("Zorki", r"\bzorki\b"),
    ("Kiev", r"\bkiev\b"),
    ("Bolex", r"\bbolex\b"),
    ("Phase One", r"\bphase ?one\b"),
    ("DJI", r"\bdji\b"),
    ("GoPro", r"\bgopro\b"),
    ("Insta360", r"\binsta ?360\b"),
    ("Blackmagic", r"\bblackmagic\b|\bbmpcc\b"),
    ("RED", r"\bred (komodo|raptor|dsmc\d?|epic|scarlet)\b"),
    ("Atomos", r"\batomos\b"),
    ("Godox", r"\bgodox\b"),
    ("Profoto", r"\bprofoto\b"),
    ("Metz", r"\bmetz\b"),
    ("Nissin", r"\bnissin\b"),
    ("Phottix", r"\bphottix\b"),
    ("PocketWizard", r"\bpocket ?wizard\b"),
    ("Elinchrom", r"\belinchrom\b"),
    ("Broncolor", r"\bbroncolor\b"),
    ("Hensel", r"\bhensel\b"),
    ("Bowens", r"\bbowens\b"),
    ("Visatec", r"\bvisatec\b"),
    ("Aputure", r"\baputure\b"),
    ("Nanlite", r"\bnanlite\b|\bnanguang\b"),
    ("Litepanels", r"\blite ?panels\b"),
    ("K5600", r"\bk5600\b"),
    ("Westcott", r"\bwestcott\b"),
    ("Sekonic", r"\bsekonic\b"),
    ("Gossen", r"\bgossen\b"),
    ("Manfrotto", r"\bmanfrotto\b"),
    ("Gitzo", r"\bgitzo\b"),
    ("Benro", r"\bbenro\b"),
    ("Really Right Stuff", r"\breally right stuff\b|\brrs\b"),
    ("Leofoto", r"\bleofoto\b"),
    ("Acratech", r"\bacratech\b"),
    ("Vanguard", r"\bvanguard\b"),
    ("Joby", r"\bjoby\b|\bgorillapod\b"),
    ("Tiltall", r"\btiltall\b"),
    ("Arca-Swiss", r"\barca[- ]swiss\b"),
    ("Kirk", r"\bkirk\b"),
    ("Peak Design", r"\bpeak design\b"),
    ("Lowepro", r"\blowepro\b"),
    ("Think Tank", r"\bthink ?tank\b"),
    ("Tenba", r"\btenba\b"),
    ("Billingham", r"\bbillingham\b"),
    ("Domke", r"\bdomke\b"),
    ("Pelican", r"\bpelican\b"),
    ("Wandrd", r"\bwandrd\b"),
    ("BlackRapid", r"\bblack ?rapid\b"),
    ("SmallRig", r"\bsmall ?rig\b"),
    ("Tilta", r"\btilta\b"),
    ("Zhiyun", r"\bzhiyun\b"),
    ("Rode", r"\br(o|ø)de\b"),
    ("Sennheiser", r"\bsennheiser\b"),
    ("Shure", r"\bshure\b"),
    ("Tascam", r"\btascam\b"),
    ("Tether Tools", r"\btether ?tools\b|\btetherpro\b"),
    ("Vivitar", r"\bvivitar\b"),
    ("Soligor", r"\bsoligor\b"),
    ("Kiron", r"\bkiron\b"),
    ("Helios", r"\bhelios\b"),
    ("Jupiter", r"\bjupiter\b"),
    ("Industar", r"\bindustar\b"),
    ("Tair", r"\btair\b"),
    ("Zenit", r"\bzenit\b"),
    ("Kenko", r"\bkenko\b"),
    ("Hoya", r"\bhoya\b"),
    ("B+W", r"\bb\+w\b"),
    ("Tiffen", r"\btiffen\b"),
    ("Cokin", r"\bcokin\b"),
    ("NiSi", r"\bnisi\b"),
    ("Lee Filters", r"\blee (filters?|100|85|sw150|seven5)\b"),
    ("Heliopan", r"\bheliopan\b"),
    ("Mitakon", r"\bmitakon\b|\bzhongyi\b"),
    ("Meike", r"\bmeike\b"),
    ("Pergear", r"\bpergear\b"),
    ("Neewer", r"\bneewer\b"),
    ("Yongnuo", r"\byongnuo\b"),
    ("Metabones", r"\bmetabones\b"),
    ("Fotodiox", r"\bfotodiox\b"),
    ("Fotga", r"\bfotga\b"),
    ("Commlite", r"\bcommlite\b"),
    ("Kipon", r"\bkipon\b"),
    ("Novoflex", r"\bnovoflex\b"),
    ("Lomography", r"\blomo(graphy)?\b"),
    ("SanDisk", r"\bsandisk\b"),
    ("Lexar", r"\blexar\b"),
    ("Epson", r"\bepson\b"),
    ("Wacom", r"\bwacom\b"),
    ("Datacolor", r"\bdatacolor\b|\bspyder\s?x?\d\b"),
]
FIRST_PARTY = {"Canon", "Nikon", "Sony", "Fujifilm", "Panasonic", "Olympus", "OM System", "Leica", "Pentax", "Hasselblad"}
# Independent lens makers: when one is named, it is the brand even if a mount brand appears first
# ("Canon EF mount Sigma 35mm"). Accessory brands do not get this boost ("Nikon D850 + Peak Design strap").
LENS_MAKERS = {"Sigma", "Tamron", "Tokina", "Zeiss", "Voigtlander", "Samyang", "Viltrox", "Laowa", "TTArtisan",
               "7Artisans", "Thypoch", "Artizlab", "Sirui", "Irix", "Lensbaby", "Schneider", "Rodenstock", "Vivitar",
               "Soligor", "Kiron", "Helios", "Jupiter", "Industar", "Tair", "Mitakon", "Meike", "Pergear", "Kenko",
               "Yongnuo", "Neewer", "Cosina"}
# Shopify "vendor" values and sheet columns that are not real brands
BRAND_HINT_STOP = {"", "other", "others", "misc", "used", "usage", "generic", "russian", "soviet", "unknown", "n/a",
                   "the camera store", "gosselin", "gosselin photo", "plotcamera", "plot camera", "camera trading company",
                   "camera traders", "maple camera co.", "maple camera", "cameracanada", "camera canada", "default"}


def detect_brand(text: str, hint: str = "", lens_boost: bool = True) -> str | None:
    t = f"{hint} {text}".lower()
    best = None
    best_pos = 10 ** 9
    for brand, rx in BRAND_PATTERNS:
        m = re.search(rx, t)
        if m:
            pos = m.start() - (5000 if lens_boost and brand in LENS_MAKERS else 0)
            if pos < best_pos:
                best, best_pos = brand, pos
    if best is None and hint and hint.strip().lower() not in BRAND_HINT_STOP and len(hint.strip()) <= 30:
        h = re.sub(r"\s+", " ", hint.strip())
        return h if not h.isupper() or len(h) <= 4 else h.title()  # "FOO" -> "Foo", keep "RRS"-style short codes
    return best


# ---------------------------------------------------------------- category
ACCESSORY_RX = (r"\b(bg-?\w+|blc-?\w+|mhg-?\w+|handgrip|hand grip|np-\w+|bc-\w+|mb-?[dn]?\d+|vg-?\w+|hdmi|xlr|power bank|battery pack|hood|cap|caps|filter|battery|batteries|charger|grip|strap|bag|case|backpack|tripod|monopod|head|"
                r"plate|cable|cord|remote|release|adapter|adaptor|bague|tube|tubes|extension|eyecup|viewfinder|finder|"
                r"loupe|screen|focusing screen|bellows|close-?up|diopter|bracket|mount adapter|card|reader|"
                r"pouch|cover|sunshade|step-?up|lens hood|pare-soleil|bouchon|chargeur|batterie|sac|courroie)\b")
FLASH_RX = r"\b(flash|speedlite|speedlight|strobe|softbox|light stand|monolight|monohead|led panel|ring light|trigger|transmitter|ttl|st-e\d\S*|\d{3}ex\S*|sb-?\d{3}|hvl-\S+)\b"
CAMERA_RX = r"\b(body|bo[iî]tier|camera|cam[eé]ra|dslr|slr|mirrorless|rangefinder|point\s?&\s?shoot|compact|camcorder)\b"
FOCAL_RX = r"(?<![\d.])(\d{1,4}(?:[-–]\d{1,4})?)\s?mm(?:\b|(?=f\s?/?\d))"  # "XF18-135mmF3.5" has no gap
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
APERTURE_RX = r"(?:\bf|(?<=mm)[fF]|\bF|1:|ƒ)\s?/?\s?(\d{1,2}(?:\.\d)?)(?:\s?[-–]\s?(\d{1,2}(?:\.\d)?))?"
TELECONV_RX = r"\b(teleconverter|extender|tc-?\d|ef ?\d\.\dx|\d\.\dx)\b"


# Paper, packaging and drive accessories that mention a camera/lens model but are not one ("Leica M5 Instruction Manual")
STRONG_ACCESSORY_RX = (r"\b(instruction|instructions|manual|manuals|brochure|booklet|book|guide|catalogu?e|poster|"
                       r"empty box|box only|original box|winder|motor ?drive|power ?winder|data ?back|film back|film magazine|"
                       r"lens board|focusing rail|selfie stick|cage|focusing screens?|eyepieces?|filter holder|holder system|"
                       r"holder kit|slide trays?|expodisc|tc-dc\d+\w*|(tele|wide)[- ]converter\b.{0,20}\(\d{2}mm\))(?!\w)")


FILM_CAMERA_RX = (r"\b(film|slr|bridge|instant|rangefinder|point[- ]and[- ]shoot) camera\b|\b35 ?mm (used )?(film )?slr\b|"
                  r"\bcamera body\b")
BUNDLE_JOIN_RX = r"(?<!\S)\+|\bw/|\bwith\b|\bavec\b|\bkit\b"


def is_bundle(text: str, category: str) -> bool:
    """A camera sold with a lens ("Nikon FE2 w/50F1.8", "Z fc with 16-50mm Lens"). Its price is not the body's price."""
    if category != "camera":
        return False
    t = text.lower()
    return any(find_focal(t[m.end():])[0] is not None for m in re.finditer(BUNDLE_JOIN_RX, t))


def detect_category(text: str, hint: str = "") -> str:
    t = f"{text} {hint}".lower()
    if re.search(STRONG_ACCESSORY_RX, text.lower()):
        return "accessory"
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
    if re.search(FILM_CAMERA_RX, t) and not re.search(r"\b(for|pour|fits)\b", t):
        return "camera"  # "Pentax ES 35mm Film SLR Camera Body": 35mm is the film format, not a focal length
    if has_focal or re.search(r"\blens\b|\bobjectif\b|\bnikkor\b|\bzuiko\b", t):
        if re.search(CAMERA_RX, t) and re.search(r"\b(kit|w/|with|avec)\b", t):
            return "camera"  # camera kit
        prefix = t[:fpos] if fpos > 0 else ""
        if prefix and re.search(r"\b(camera|cam[eé]ra|mirrorless|dslr|body|bo[iî]tier|rangefinder)\b", prefix) \
                and not re.search(r"\b(for|pour|lens|objectif)\b", prefix):
            return "camera"  # "Canon EOS R100 Mirrorless Camera 18-45mm Lens" is a camera kit
        jm = re.search(r"((?<!\S)\+|\bw/|\bwith\b|\bavec\b)(\s*[\w.-]+){0,2}\s*$", prefix)
        if jm and re.search(r"[a-z]", prefix[:jm.start()].replace("used", "")) \
                and not re.search(r"\b(lens|objectif|for|pour|adapter|nikkor|zuiko|summicron|elmarit|takumar|rokkor|hexanon|planar|sonnar|"
                                  r"helios|jupiter|lensbaby|ring|filter|teleconverter|extender|tc-?\d|\d\.\dx)\b", prefix[:jm.start()]):
            return "camera"  # "Nikon F55 w/ 28-80mm", "Linhof Technika w/ Xenar 105mm": body + lens kit
        if prefix and re.search(r"\+|\bw/|\bwith\b|\bavec\b|\bkit\b", prefix) and camera_model(prefix, detect_brand(prefix, lens_boost=False)):
            return "camera"  # "Nikon Z30 + 16-50mm", "PANASONIC G85 W/12-35"
        return "lens"
    if re.search(CAMERA_RX, t) or camera_model(text, detect_brand(text)):
        return "camera"
    return "accessory"


# ---------------------------------------------------------------- mount
# Checked in order; first match wins. Specific / medium-format systems come before broad shorthand.
LENS_MOUNT_RULES: list[tuple[str, str]] = [
    ("Large Format", r"\blarge format\b|\blens ?board\b|\bon .{0,20}board\b|\bcopal\b|\bsironar\b|\bsymmar\b|\bnikkor-?[wm] \d|"
                     r"\bfujinon-?[aw]\b|\bfujinon [aw] \d|\bdagor\b|\bgraflex\b|\b4\s?[x×]\s?5\b|\b8\s?[x×]\s?10\b"),
    ("Enlarging", r"\benlarg(ing|er)\b|\bcomponon\b|\brodagon\b|\bel-nikkor\b"),
    ("Hasselblad XPan", r"\bxpan\b"),
    ("Hasselblad XCD", r"\bxcd\b"),
    ("Hasselblad H", r"\bhasselblad hc\b|\bhc \d|\bhcd \d"),
    ("Hasselblad V", r"\bhasselblad v\b|\b(cf|cfi|cfe|cb)\b(?!-)(?! ?card)|\bfor hasselblad\b|\bhasselblad (planar|distagon|sonnar|tele-?tessar)\b"),
    ("Mamiya 645", r"\bmamiya 645\b|\bm645\b|\bmamiya-?sekor c\b|\bsekor c\b|\b645 (af|mount)\b|\bmamiya .{0,15}\b645\b"),
    ("Mamiya RB/RZ", r"\brb ?67\b|\brz ?67\b|\bsekor-?z\b|\bsekor z\b|\bmamiya.{0,12}\b(k/l|kl)\b"),
    ("Mamiya 7", r"\bmamiya 7\b"),
    ("Pentax 645", r"\bpentax[- ]?(fa |a |d fa |)645\b|\b645 (zoom|macro)\b|\bpentax\b.{0,25}\b645\b|\b645\b.{0,25}\bpentax\b"),
    ("Pentax 67", r"\bpentax ?6x7\b|\bpentax[- ]?67\b|\bsmc pentax 6x7\b|\b67 (macro|zoom)\b"),
    ("Bronica SQ", r"\bzenzanon-?ps\b|\bzenzanon-?s\b|\bbronica sq\b|\bsq-?a\w?\b"),
    ("Bronica ETR", r"\bzenzanon-?(e|pe|mc)\b|\bbronica etr\w*\b|\betr-?s\w?\b"),
    ("Bronica GS", r"\bzenzanon-?pg\b|\bzenanon-?pg\b|\bgs-?1\b"),
    ("Contax 645", r"\bcontax 645\b"),
    ("Contax N", r"\bcontax n\b"),
    ("Contax/Yashica", r"\bc/y\b|\by/c\b|\bcontax/yashica\b|\byashica/contax\b|\b(aej|mmj|amj)\b|\byashica (ml|ds-?b|dsb)\b|"
                       r"\bcontax\b(?! ?(645|n|g\d?|t\d?)\b)"),
    ("Contax G", r"\bcontax g\d?\b"),
    ("Canon RF", r"\brf-?s?\s?\d|\brf\b(?! ?used)|\brf(?= used)|\bcanon rf\b|\brf[- ]mount|\bfor canon rf\b|\bpour canon rf\b"),
    ("Canon EF-M", r"\bef-m\b(?!.{0,20}\bfilm\b)"),
    ("Canon EF", r"\bef-?s?\s?\d|\bef-?s?\b|\bcanon ef\b|\bef[- ]mount|\bcanon mount\b|\bfor canon\b(?! rf)|\beos\b(?!\s?r)|\bze\b"),
    ("Canon FD", r"\bfdn?\b|\bnfd\b|\bnew fd\b|\bfl\s?\d|\bcanon fl\b"),
    ("Nikon Z", r"\bnikkor z\b|\bz\s?(dx|mc)\b|\bnikon z\b|\bz[- ]mount|\bfor nikon z\b|\bpour nikon z\b|\bz \d{2,3}mm|\bnikkor z\d|"
                r"\bnikon s \d|\bmonture z\b|\bcont\.? nikon z\b"),
    ("Nikon F", r"\baf-?[spdi]\b|\bai-?s?\b|\bnikon f\b|\bf[- ]mount|\bnikon mount\b|\bfor nikon\b(?! z)|\bpour nikon\b(?! z)|\bnikkor\b|"
                r"\bzf\.2\b|\bzf2\b|\bnon-?ai\b"),
    ("Sony A", r"\bsal\s?\d|\ba[- ]mount\b|\bminolta af\b|\bmaxxum\b|\bdynax\b|\bsony a \d|\bsony a(?= \d)|\bsony dt\b|\bdt \d|\bssm\b|"
               r"\bfor sony a\b|\bsony alpha a\b"),
    ("Sony E", r"\bfe\s?\d|\bsel\s?\d|\bsony e\b|\be[- ]mount|\bfor sony\b(?! a)|\bpour sony\b|\bsony fe\b|\bdi iii\b|\bdn\b|"
               r"\bmonture (e|fe)\b|\bsonnar e\b|\bbatis\b|\bloxia\b|\bnex\b"),
    ("Fujifilm G", r"\bgf\s?\d|\bg[- ]mount\b|\bfor gfx\b|\bgfx\b|\bfujifilm gf\b"),
    ("Fujifilm X", r"\bxf\s?\d|\bxc\s?\d|\bx[- ]mount|\bfor fuji(film)? x\b|\bfuji(film)? x\b|\bfor fuji(film)?\b|\bmonture x\b"),
    ("Olympus OM", r"\bolympus om\b(?!-?d)(?! system)|\bom[- ]mount\b|\bfor olympus om\b|\b[ghef]\.\s?zuiko\b|\bzuiko (mc )?auto\b|"
                   r"\bzuiko auto-\w\b|\bolympus (om )?zuiko \d"),
    ("Micro Four Thirds", r"\bm4/3\b|\bmft\b|\bmicro (four|4)[- ]thirds\b|\bm\.?\s?zuiko\b|\blumix g\b|\bleica dg\b|\bm43\b|\bmu-?4/3\b"),
    ("Four Thirds", r"\bfour thirds\b|\bzuiko digital\b"),
    ("L-Mount", r"\bl[- ]mount\b|\bmonture l\b|\blumix s\b|\bfor l\b|\bleica sl\b|\bleica tl?\b|\bleica l\b|\bvario-elmarit-sl\b|"
                r"\bsummicron-sl\b|\bapo-summicron-sl\b|\bvario-elmar-sl\b"),
    ("Leica R", r"\bleica r\b|\b(summicron|elmarit|summilux|elmar|telyt)\b.{0,30}\br\b(?!-)|\br[- ]mount\b|\b(elmarit|summicron|summilux|elmar|apo-telyt|vario-elmar|macro-elmarit|telyt)-r\b"),
    ("Leica M", r"\bleica m\b|\bm[- ]mount\b|\bvm\b|\bzm\b|\bm39\b|\bltm\b|\bl39\b|\bfor leica\b(?! [rlst]\b)"),
    ("Pentax K", r"\bpentax-?[mafd]\b|\bp/k\b|\bpk\b|\bpentax k\b|\bk[- ]mount|\bsmc\b|\bda\s?\d|\bfa\s?\d|\bd fa\b|\bdfa\b|"
                 r"\bfor pentax\b|\bpour pentax\b"),
    ("M42", r"\bm42\b|\btakumar\b|\bhelios\b|\bzenitar\b|\bspotmatic\b"),
    ("Minolta MD", r"\bminolta (md|mc)\b|\bmd rokkor\b|\bmc rokkor\b|\bsr[- ]mount\b|\brokkor-?x\b|\bfor minolta\b(?! af)|\bminolta sr\b"),
    ("Konica AR", r"\bkonica ar\b|\bhexanon ar\b|\bar[- ]mount\b|\bkonica (hexanon|mount)\b"),
    ("PL", r"\bpl[- ]mount\b|\bpl\b(?=.*\b(t\d|cine)\b)|\barri pl\b"),
]
# Brand names that, inside a third-party lens title, imply a mount ("Tamron 90F2.8 AF MACRO NIKON").
MOUNT_WORDS: list[tuple[str, str]] = [
    (r"\b(\w+ )?z\b(?!-)", "Nikon Z"), (r"\bnik(on)?\b", "Nikon F"), (r"\bcan(on)?\b", "Canon EF"), (r"\bsony\b", "Sony E"), (r"\bpentax\b", "Pentax K"),
    (r"\bfuji(film)?\b", "Fujifilm X"), (r"\bleica\b", "Leica M"), (r"\bolympus\b", "Micro Four Thirds"),
    (r"\bminolta\b(?!.*\baf\b)", "Minolta MD"), (r"\bpanasonic\b", "Micro Four Thirds")
]
FIXED_LENS_RX = (r"\bcoolpix\b|\bx100\w*\b|\bx70\b|\bx30\b|\bxf10\b|\bx-?half\b|\bleica (q\d?|x\d?|d-lux\w*|c-lux\w*)\b|\bq[23]\b(?! ?mount)|"
                 r"\brx(1|10|100)\w*\b|\bdsc-\w+|\bzv-?1\w*\b|\blx\s?\d+\b|\bdmc-(lx|tz|zs|fz)\w*|\bdc-(lx|tz|zs|fz)\w*|\bpowershot\b|"
                 r"\bixus\b|\belph\b|\bg(1|5|7|9) ?x\b|\bricoh gr\w*\b|\bgr ?(ii|iii|iv)x?\b|\btheta\b|\bpoint[\s-]*(&|and)?[\s-]*shoot\b|\bespio\b|"
                 r"\bcompact camera\b|\bcyber-?shot\b|\bfinepix\b|\bcamcorder\b|\bcontax t\d\b|\bolympus (mju|stylus|xa|tough)\b|"
                 r"\bdisposable\b|\binstant camera\b|\binstax\b|\bpolaroid\b|\bxf\d{2,3}\b(?= ?camcorder)")
CAMERA_MOUNT_RULES: list[tuple[str | None, str, str]] = [
    (None, FIXED_LENS_RX, "Fixed Lens"),
    (None, r"\bxpan\b", "Hasselblad XPan"),
    ("Hasselblad", r"\bx(1d|2d)\w*\b|\b907x\b", "Hasselblad XCD"),
    ("Hasselblad", r"\bh\d[a-z]*\b", "Hasselblad H"),
    ("Hasselblad", r"\b(500|501|503|553|555|2000|201|203|205)\s?\w*\b", "Hasselblad V"),
    ("Mamiya", r"\bm?645\w*\b", "Mamiya 645"),
    ("Mamiya", r"\br[bz]\s?67\w*\b", "Mamiya RB/RZ"),
    ("Mamiya", r"\bmamiya 7\b", "Mamiya 7"),
    ("Bronica", r"\bsq\w*\b", "Bronica SQ"), ("Bronica", r"\betr\w*\b", "Bronica ETR"), ("Bronica", r"\bgs-?1\b", "Bronica GS"),
    ("Pentax", r"\b645\w*\b", "Pentax 645"), ("Pentax", r"\b6x7\b|\b67\b", "Pentax 67"),
    ("Contax", r"\bcontax g\d?\b|\bg[12]\b", "Contax G"), ("Contax", r"\b645\b", "Contax 645"),
    ("Contax", r"\b(rts|aria|167|137|139|159|rx|st|ax)\w*\b", "Contax/Yashica"),
    ("Yashica", r"\b(fx|fr|electro ax|contax)\b|\bfx-?\d\b|\bfr ?i*\b", "Contax/Yashica"),
    (None, r"\bleica l\b|\bl[- ]mount\b", "L-Mount"),
    (None, r"\bpl[- ]mount\b", "PL"),
    ("Canon", r"\b(eos\s?)?r(1|3|5|5c|6|7|8|10|50|50v|100|p)\b|\beos r\b", "Canon RF"),
    ("Canon", r"\b(ae-?1|a-?1|at-?1|av-?1|al-?1|t50|t60|t70|t80|t90|f-?1|ftb|tx|tlb)\w*\b|\bfd\b", "Canon FD"),
    ("Canon", r"\beos\s?m\d*\b|\bm(50|6|100|200)\b", "Canon EF-M"),
    ("Canon", r"\b(\d{1,3}d|rebel|t\d+i?|sl\d|1d[sx]?|5ds?r?|elan|eos)\w*\b|\bc(100|200|300|500)\b|\bef-m 35mm film\b", "Canon EF"),
    ("Nikon", r"\bz\s?(5|6|7|8|9|f|fc|30|50|r|6ii|7ii)\w*\b|\bzf\b|\bzfc\b|\bzr\b", "Nikon Z"),
    ("Nikon", r"\bd\d{1,4}[a-z]?\b|\bf\d\w*\b|\bfm\d?\w*\b|\bfe\d?\b|\bf100\b|\bft(n|2|3)?\b|\bfg(-20)?\b|\bem\b|\bn\d{2,4}\b|"
              r"\bnikkormat\b|\bel2?\b|\bfa\b", "Nikon F"),
    ("Sony", r"\bslt-\w+|\ba(33|35|37|55|57|58|65|68|77|99|100|200|230|290|300|330|350|380|390|500|550|560|580|700|850|900)\b|"
             r"\bdslr-a\d+", "Sony A"),
    ("Sony", r"\b(alpha\s?|a|α|ilce-?)(7|9|1|6\d{3}|7c|7r|7s|7cr)\w*\b|\bzv-?e\d+\b|\bfx(3|30|6|2)\b|\bnex", "Sony E"),
    ("Minolta", r"\b(maxxum|dynax|alpha|\d{3,4}si|\d{3,4}xi|[2-9]000i?|a\d)\w*\b", "Sony A"),
    ("Minolta", r"\b(x-?\d{3}|xd\w*|xe\w*|xg\w*|srt\w*|sr-?\w+|xk|x-?370|x-?700)\b", "Minolta MD"),
    ("Fujifilm", r"\bgfx\b", "Fujifilm G"),
    ("Fujifilm", r"\bx-?(t|s|e|h|pro|a|m)\s?\d", "Fujifilm X"),
    ("Panasonic", r"\blumix s\d|\bs(1|5|9)\w*\b|\bdc-s\d", "L-Mount"),
    ("Panasonic", r"\b(gh|g|gx|gf)\s?\d", "Micro Four Thirds"),
    ("Olympus", r"\b(e-?m\d|pen|om-?d|e-?p\d|e-?pl\d)\b", "Micro Four Thirds"),
    ("Olympus", r"\bom-?(1|2|3|4|10|20|30|40|pc)\w*\b|\bom10\b", "Olympus OM"),
    ("Olympus", r"\be-?(1|3|5|30|300|330|400|410|420|450|500|510|520|600|620)\b", "Four Thirds"),
    ("OM System", r"\bom-?\d\b|\bom-5\b", "Micro Four Thirds"),
    ("Leica", r"\bleica m\d*\b|\bm(2|3|4|5|6|7|8|9|10|11)(-?[a-z]{1,2})?\b|\bm-?(d|e|p|a)\b|\bmp\b", "Leica M"),
    ("Leica", r"\br(3|4|5|6|7|8|9|e)\w*\b|\bleicaflex\b", "Leica R"),
    ("Leica", r"\bsl\d?\b|\bcl\b|\btl2?\b", "L-Mount"),
    ("Pentax", r"\bk-?\d+\w*\b|\bkp\b|\b(mx|me( super| f)?|mv1?|lx|kx|km|k2|p30t?|p3n?|p5|pz-?\d+|program a|super a|super program|zx-?\d+|mz-?\w+)\b|\*ist|"
               r"\bk1000\b", "Pentax K"),
    ("Pentax", r"\bspotmatic\b|\bsp\s?(ii|500|1000|f)?\b|\besii?\b", "M42"),
    ("Ricoh", r"\bxr-?\w+|\bkr-?\w+", "Pentax K"),
    ("Zenit", r".", "M42"), ("Praktica", r"\bmtl|\bltl|\bplc|\bsuper tl|\bnova|\bpraktica\b", "M42"),
    ("Konica", r"\b(autoreflex|t3|tc|fs-?1|fc-?1|ft-?1|fp-?1)\w*\b", "Konica AR"),
    ("Blackmagic", r"\b(pocket|bmpcc).{0,25}\b6k\b|\bef\b", "Canon EF"),
    ("Blackmagic", r"\bcinema camera 6k\b|\bpyxis\b", "L-Mount"),
    ("Blackmagic", r"\b(pocket|bmpcc).{0,25}\b4k\b|\bmicro four|\bmft\b", "Micro Four Thirds"),
]


def detect_mount(text: str, brand: str | None, category: str, hint: str = "") -> str | None:
    t = f"{text} {hint}".lower()
    if category == "camera":
        for b, rx, mount in CAMERA_MOUNT_RULES:
            if (b is None or brand == b) and re.search(rx, t):
                return mount
        return None
    if category not in {"lens", "accessory", "flash/lighting"}:
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
            if mount in {"Large Format", "Enlarging"} and category != "lens":
                continue
            if mount == "Hasselblad V" and not re.search(r"hassel|planar|distagon|sonnar|zeiss|makro|tessar|biogon", t):
                continue
            return mount
    if category != "lens":
        return None
    # third-party lens naming the mount brand without "for"/"mount" ("SIGMA 17-50 F2.8 DC HSM NIK")
    if brand and brand not in FIRST_PARTY:
        for rx, mount in MOUNT_WORDS:
            if re.search(rx, t):
                return mount
    # brand defaults for first-party lenses where shorthand is absent
    if brand == "Fujifilm" and "instax" not in t:
        return "Fujifilm X"
    if brand == "Olympus" and "om-" not in t:
        return "Micro Four Thirds" if "digital" not in t else "Four Thirds"
    if brand == "OM System":
        return "Micro Four Thirds"
    if brand == "Panasonic":
        return "Micro Four Thirds"
    if brand == "Sony":
        return "Sony E"  # A-mount markers (SAL, DT, SSM, "Sony A 100mm") are caught above
    if brand == "Nikon" and not re.search(r"\b1 nikkor\b|\bnikon 1\b|\bcoolpix\b", t):
        return "Nikon F"
    if brand == "Leica":
        focal, _, _ = find_focal(t)
        if focal and "-" in focal and "tri-elmar" not in t:
            return "L-Mount"  # Leica zooms without an R marker are SL/TL lenses
        return "Leica M"  # SL/TL/R/DG markers are caught above
    if brand == "Hasselblad":
        return "Hasselblad V"
    if brand == "Pentax":
        return "Pentax K"
    if brand == "Mamiya" and "sekor" in t:
        return "Mamiya 645"
    return None


# ---------------------------------------------------------------- condition
GRADES = ["Like New", "Excellent", "Good", "Fair", "As Is"]
CONDITION_RULES: list[tuple[str, str]] = [
    ("As Is", r"\bas[- ]is\b|\bfor parts\b|\bparts only\b|\bdefective\b|\bnot working\b|\bfungus\b|\bpour pi[eè]ces\b|"
              r"\bfor repair\b|\bbroken\b|\bnon[- ]functional\b"),
    ("Like New", r"\(ln-?\)|\bln-?\b|\blike new\b|\bnear mint\b|\bmint\b|\bminty\b|\*a\+\*|\ba\+|\bopen[- ]box\b|\bdemo\b|"
                 r"\bnew in box\b|\bnew old stock\b|\bnos\b|\bcomme neuf\b|\busag[ée]e?\s*\(n\)|\b(9\.5|10)\s?/\s?10\b|"
                 r"\b(10|9\+)\b(?=\s*\)|\s*$)"),
    ("Excellent", r"\b(light|minimal|minor|very light) (cosmetic )?(wear|marks)\b|\bvery clean\b|\(ex\+?\)|\bex\+?(?=[\s)\]*,.-]|$)(?! ?(dg|dc|hsm|apo|asp\w*|macro|if|\d))|\bexc\b|\bexcellent\b|\*a\*|"
                  r"\b9\s?/\s?10\b"),
    ("Good", r"\b(some|moderate|normal) (cosmetic )?(wear|marks|scuffs)\b|\bsigns of (use|wear)\b|\bvery good\b|\btr[eè]s bon\b|\bvg\+?(?=[\s)\]*,.-]|$)|\bgood\b|\bgd\b|\*b\+?\*|\b8\s?/\s?10\b|\bbon [ée]tat\b"),
    ("Fair", r"\(bgn\)|\bbgn\b|\bbargain\b|\bfair\b|\bpoor\b|\*c\*|\b[5-7]\s?/\s?10\b|\bwell used\b|\b(heavy|significant|considerable) (cosmetic )?wear\b|\bwell worn\b|\bud\b"),
]
# Gosselin titles start "USAGE (8) - ...". The number is Gosselin's own condition grade, per their published scale
# (https://gosselinphoto.ca/pages/echelle-evaluation-produits-usages, checked 2026-10-18): N = new in box with all
# accessories; 9 = 97-99% of original condition, minimal wear; 8 = 80-96%, normal wear, light marks, no effect on
# images; 7 = 70-79%, above-average wear, scuffs/dents, no effect on images; 6 = deep scratches/dents, lens marks that
# affect image quality. Mapped below to Like New / Excellent / Good / Fair / Fair.
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
    # Drop apertures so "Nikon F55 w/ 28-80mm f3.5" or "Nikon Df + 50mm f1.8" do not read as an F3 / F1 body
    t = re.sub(r"(?<![a-z])f/?\s?\d{1,2}\.\d+|(?<=\d)f/?\d{1,2}(?:\.\d+)?", " ", t)
    pats = {
        "Canon": r"(?<![-/\w])(?:eos\s?)?(r\d{1,3}[a-z]?|(?<=eos )r|rp|\d{1,4}d[sxr]{0,2}|rebel\s?[a-z]{1,2}\d*i?|m\d{0,3}|g\d{1,2}x?|powershot\s?\w+|ae-?1(?:\s?program)?|at-?1|av-?1|al-?1|a-?1|t(?:50|60|70|80|90)|f-?1n?|ftb\w?|elan\s?\w+)"
                 r"(?:\s?(?:mark|mk|m)\s?(ii|iii|iv|2|3|4))?\b",
        "Nikon": r"\b(z\s?\d{1,2}|zf|zfc|z\s?fc|d\d{1,4}[a-z]?|f\d|fm\d?|fe\d?|coolpix\s?\w+)\s?(ii|iii)?\b",
        "Sony": r"\b(?:alpha|a|α|ilce-?)\s?(7|9|1|7c|7r|7s|7cr|6\d{3}|99|77|68)\s?(?:(ii|iii|iv|v)|m(\d))?\b|\b(rx\d{1,3})\s?(?:(ii|iii|iv|v|vi|vii)|m(\d))?\b|\b(zv-?e\d{1,2}|fx\d{1,2})\b",
        "Fujifilm": r"\b(x-?(?:t|s|e|h|pro|a|m)\s?\d{1,3}[a-z]?|x100\s?[a-z]{0,2}|gfx\s?\d{2,3}[a-z]{0,2}|x-?\d{2}|xf\d{2})\s?(ii)?\b",
        "Panasonic": r"\b(?:dc-|dmc-)?(gh\d[a-z]?|g\d{1,3}|gx\d{1,3}|s\d[a-z]{0,2}|lx\d{1,3})\s?(ii)?\b",
        "Olympus": r"\b(e-?m\d{1,2})\s?(?:mark|mk)?\s?(ii|iii|iv)?\b|\b(om-?\d|pen-?f|e-?p\d)\b",
        "OM System": r"\b(om-?\d)\s?(ii)?\b",
        "Leica": r"\b(m\d{1,2}[a-z-]*|q\d?|sl\d?|cl|tl\d?)\b",
        "Pentax": r"\b(k-?\d{1,4}[a-z]{0,2}|kp|k1000|me super|spotmatic|67)\s?(ii)?\b",
        "Ricoh": r"\b(gr\s?(?:iii|iv|ii)x?|gr\d?)\b",
        "Minolta": r"\b(x-?\d{3}|xd-?\d{0,2}|xe-?\d?|xg-?\w+|srt-?\s?\d{3}|maxxum \d{4}\w*|dynax \d+\w*|[2-9]000i?|\d{3}si)\b",
        "Hasselblad": r"\b(500\s?c/?m|500\s?c|501\s?cm?|503\s?cw|503\s?cx|x1d\s?ii|x1d|x2d|907x|h\d[a-z]{0,2})\b",
        "Mamiya": r"\b(rb\s?67|rz\s?67|m?645\s?(?:pro tl|pro|super|1000s|j|af)?|7\s?ii|6)\b",
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


GOSSELIN_PREFIX_RX = re.compile(r"^\s*usag[ée]e?s?\s*\(\s*(?:\d{1,2}|n)\s*\)\s*[-–:]?\s*", re.I)
# Only translate "pour" when a camera brand or mount follows, where it can only mean "for".
POUR_RX = re.compile(r"\bpour\s+(?=(canon|nikon|sony|fuji|fujifilm|pentax|olympus|om[- ]system|leica|minolta|panasonic|"
                     r"sigma|hasselblad|mamiya|contax|m42|micro\s?4/3|micro four thirds|l[- ]mount|monture)\b)", re.I)
MONTURE_RX = re.compile(r"\bfor\s+monture\s+([A-Za-z0-9/-]+)", re.I)


def display_title(t: str) -> str:
    """Reader-facing title: drops Gosselin's "USAGE (8) - " prefix (the grade is kept in the condition field) and
    turns "pour Canon FD" / "pour monture M42" into "for Canon FD" / "for M42 mount". The raw title is kept as
    title_raw, and all matching (brand, model, condition) still runs on the raw title."""
    d = GOSSELIN_PREFIX_RX.sub("", t)
    d = POUR_RX.sub("for ", d)
    d = MONTURE_RX.sub(lambda m: f"for {m.group(1)} mount", d)
    return d.strip() or t


def parse_price(p) -> float | None:
    if p is None or p == "":
        return None
    try:
        v = float(re.sub(r"[^\d.]", "", str(p)))
        return round(v, 2) if v > 0 else None
    except ValueError:
        return None


# Dealer-supplied mount labels (e.g. Shopify tags "lens mount_Nikon F") -> our canonical names
MOUNT_ALIASES = {
    "nikon f": "Nikon F", "nikon z": "Nikon Z", "canon ef": "Canon EF", "canon ef-s": "Canon EF", "canon rf": "Canon RF",
    "canon ef-m": "Canon EF-M", "canon fd": "Canon FD", "sony e": "Sony E", "sony fe": "Sony E", "sony a": "Sony A",
    "fujifilm x": "Fujifilm X", "fuji x": "Fujifilm X", "fujifilm g": "Fujifilm G", "micro four thirds": "Micro Four Thirds",
    "four thirds": "Four Thirds", "l-mount": "L-Mount", "l mount": "L-Mount", "leica l": "L-Mount", "leica m": "Leica M",
    "leica r": "Leica R", "pentax k": "Pentax K", "m42": "M42", "olympus om": "Olympus OM", "minolta md": "Minolta MD",
    "minolta sr": "Minolta MD", "hasselblad v": "Hasselblad V", "mamiya 645": "Mamiya 645", "contax/yashica": "Contax/Yashica",
}


def make_listing(dealer_id: str, dealer: str, title: str, price, url: str, *, sku: str | None = None,
                 in_stock: bool = True, condition_hint: str = "", category_hint: str = "", brand_hint: str = "",
                 fetched_at: str, source: str = "dealer", image: str | None = None, location: str | None = None,
                 mount_hint: str = "") -> dict:
    title = clean_title(title)
    ident = sku or url or title
    lid = f"{dealer_id}-" + hashlib.sha1(f"{ident}|{title if not sku else ''}".encode()).hexdigest()[:10]
    override = listing_overrides().get(lid, {})
    brand = detect_brand(title, brand_hint)
    category = override.get("category") or detect_category(title, category_hint)
    if category == "camera":  # "Sony A7 III + Sigma 35mm" is a Sony camera, not a Sigma
        brand = detect_brand(title, brand_hint, lens_boost=False)
    mount = (MOUNT_ALIASES.get(mount_hint.strip().lower()) if mount_hint else None) \
        or detect_mount(title, brand, category, category_hint)
    condition = detect_condition(title, condition_hint)
    if category == "lens":
        model_key, model_name = lens_key(title, brand, mount)
    elif category == "camera":
        model_key, model_name = camera_key(title, brand)
    else:
        model_key, model_name = None, None
    if "model_key" in override and override["model_key"] is None:
        model_key, model_name = None, None
    out = {
        "id": lid, "dealer_id": dealer_id, "dealer": dealer, "source": source, "title": display_title(title),
        "title_raw": title,
        "brand": brand, "mount": mount, "category": category, "condition": condition,
        "model_key": model_key, "model_name": model_name, "price_cad": parse_price(price), "url": url,
        "in_stock": bool(in_stock), "image": image, "location": location, "fetched_at": fetched_at,
    }
    if override.get("bundle", is_bundle(title, category)):
        out["bundle"] = True
    return out


_OVERRIDES: dict | None = None


def listing_overrides() -> dict:
    """Hand-checked per-listing fixes (data/listing-overrides.json), keyed by stable listing id.
    Each entry may set "category", "model_key": null (keep off model pages) and/or "bundle"."""
    global _OVERRIDES
    if _OVERRIDES is None:
        import json
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "data" / "listing-overrides.json"
        try:
            _OVERRIDES = json.loads(p.read_text()).get("listings", {})
        except (OSError, ValueError):
            _OVERRIDES = {}
    return _OVERRIDES
