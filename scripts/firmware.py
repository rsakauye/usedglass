#!/usr/bin/env python3
"""Refresh data/firmware.json from manufacturers' official firmware pages. Run by hand, not in the daily scrape:

    python3 scripts/firmware.py            # rewrite data/firmware.json
    python3 scripts/firmware.py --dry-run  # print what would change

Sources (official only, a few index pages, not one page per model where avoidable):
  Fujifilm   fujifilm-x.com firmware news (WordPress API: release date + version + model page), version cross-checked
             against the model's firmware page
  Nikon      downloadcenter.nikonimglib.com yearly "update history" pages (date + "<model> Firmware Version x")
  Panasonic  av.jpn.support.panasonic.com Micro Four Thirds / full-frame firmware tables (version + date)
  OM System  support.jp.omsystem.com interchangeable-lens camera/lens firmware table (version + date)
  Ricoh      ricoh-imaging.co.jp download index, then each model's page for version + YYYY/MM/DD date
A model is left out unless both version and date were read from the official page. Never guessed.
Attention notes are curated by hand in data/firmware.json ("attention", "attention_source"); this script keeps them
only while the latest version is unchanged, so a note never sticks to a newer release.
Not covered yet: Canon, Sony, Leica, Hasselblad, Sigma, Tamron (official pages block scripted fetches or have no index).
"""
import datetime as dt, html, json, re, sys, urllib.error, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "firmware.json"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120 UsedGlass-firmware-check"}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code < 500:
                print(f"  ! {url}: {e}", file=sys.stderr)
                return ""
        except Exception as e:
            if i == tries - 1:
                print(f"  ! {url}: {e}", file=sys.stderr)
    return ""


def text(h):
    h = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", h, flags=re.S)
    return re.sub(r"(\s*\|\s*)+", " | ", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " | ", h))))


def mdy(s):  # "Apr. 25, 2022" / "Nov. 04, 2025"
    m = re.match(r"([A-Za-z]{3})[a-z]*\.?\s*(\d{1,2}),\s*(\d{4})", s.strip())
    return f"{m[3]}-{MONTHS[m[1].lower()]:02d}-{int(m[2]):02d}" if m and m[1].lower() in MONTHS else None


norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())


def lens_sig(name):
    """'Fujifilm 16-55mm f/2.8 LM (Fujifilm X)' -> ('16-55', '28', has_ii)"""
    m = re.search(r"(\d+(?:-\d+)?)mm(?: f/([\d.]+(?:-[\d.]+)?))?", name)
    return (m[1], (m[2] or "").replace(".", "").replace("-", ""), bool(re.search(r"\bII\b", name))) if m else None


def match_lens(sig, cands):
    """cands: list of (focal, apdigits, has_ii, payload). Unique match on focal+aperture (+ Mark II) or None."""
    if not sig or not sig[1]:
        return None
    hits = [c for c in cands if c[0] == sig[0] and c[1] == sig[1]]
    hits = [c for c in hits if c[2] == sig[2]]  # Mark II and Mark I lenses have separate firmware
    keys = {json.dumps(c[3], sort_keys=True) for c in hits}
    return hits[0][3] if len(keys) == 1 else None


def fujifilm(models):
    out, news, page = {}, [], 1
    while page < 10:
        b = get(f"https://www.fujifilm-x.com/global/wp-json/wp/v2/news?search=firmware&per_page=100&page={page}&_fields=date,title,link")
        try:
            items = json.loads(b)
        except Exception:
            break
        if not isinstance(items, list) or not items:
            break
        news += items
        page += 1
    base = "https://www.fujifilm-x.com/global/support/download/firmware/"
    latest = {}  # model page url -> (date, version)
    for n in news:
        t = html.unescape(n["title"]["rendered"])
        v = re.search(r"Ver\.?\s?(\d+\.\d+)", t)
        if not v or "/firmware/" not in n["link"]:
            continue
        d = n["date"][:10]
        p = re.search(r"/firmware/((?:cameras|lenses)/[^/\s]+)/", n["link"].replace(" ", ""))
        if not p:
            continue
        link = base + p[1] + "/"  # the API mixes /global/ and regionless links; use the global page
        if link not in latest or d > latest[link][0]:
            latest[link] = (d, v[1])
    lens_c = []
    for link, (d, v) in latest.items():
        m = re.search(r"/lenses/((?:xf|xc|gf)(\d+(?:-\d+)?)mm[ft](\d+(?:-\d+)*)[^/]*)/", link)
        if m:
            lens_c.append((m[2], m[3].replace("-", ""), bool(re.search(r"-ii(-|$)", m[1])), {"link": link, "d": d, "v": v, "gf": m[1].startswith("gf")}))
    for k, mo in models.items():
        if mo["brand"] != "Fujifilm":
            continue
        if mo["category"] == "camera":
            slug = re.sub(r"^x(?=[a-z])", "x-", mo["name"].replace("Fujifilm ", "").lower()).replace(" ", "-")
            link = f"{base}cameras/{slug}/"
            hit = latest.get(link)
            hit = hit and {"link": link, "d": hit[0], "v": hit[1]}
        elif mo["category"] == "lens" and mo["mount"] in ("Fujifilm X", "Fujifilm G"):
            hit = match_lens(lens_sig(mo["name"]), [c for c in lens_c if c[3]["gf"] == (mo["mount"] == "Fujifilm G")])
        else:
            continue
        if not hit:
            continue
        vers = re.findall(r"firmware update Ver\.\s?(\d+\.\d+)", text(get(hit["link"])), re.I)  # "The firmware update Ver.4.31 from Ver.4.30"
        top = max(vers, key=lambda x: tuple(map(int, x.split("."))), default=None)
        if top != hit["v"]:  # the page knows a newer release than the dated news post: no confirmed date, leave out
            print(f"  ? {k}: news says {hit['v']}, page's newest is {top}; skipped", file=sys.stderr)
            continue
        out[k] = {"version": hit["v"], "released": hit["d"], "url": hit["link"]}
    return out


def nikon(models):
    rel = {}  # normalized product -> (date, version, url)
    for y in range(2014, dt.date.today().year + 1):
        h = get(f"https://downloadcenter.nikonimglib.com/en/update/index/{y}.html")
        for d, href, title in re.findall(r'<span class="date">(\d{4}-\d{2}-\d{2})</span>.*?<a href="(/en/download/fw/\d+\.html)">([^<]+)</a>', h, re.S):
            if d <= "2014-10-01":
                continue  # the download centre's launch date, stamped on older releases: not a real release date
            m = re.match(r"(.+?)\s+Firmware(?:\s+\w)?\s+Version\s+([\d.]+)", html.unescape(title).strip())
            if not m:
                continue
            for prod in m[1].split("/"):
                p = norm(prod)
                if p and (p not in rel or d > rel[p][0]):
                    rel[p] = (d, m[2], "https://downloadcenter.nikonimglib.com" + href, m[1])
    lens_c = []
    for p, (d, v, u, title) in rel.items():
        if "nikkor" in p:
            s = lens_sig(title.replace(" f/", "mm f/") if "mm" not in title else title)
            if s:
                lens_c.append((s[0], s[1], s[2], {"d": d, "v": v, "u": u}))
    out = {}
    for k, mo in models.items():
        if mo["brand"] != "Nikon":
            continue
        if mo["category"] == "camera":
            hit = rel.get(norm(mo["name"].replace("Nikon ", "")))
            hit = hit and {"d": hit[0], "v": hit[1], "u": hit[2]}
        elif mo["category"] == "lens" and mo["mount"] == "Nikon Z":
            hit = match_lens(lens_sig(mo["name"]), lens_c)
        else:
            continue
        if hit:
            out[k] = {"version": hit["v"], "released": hit["d"], "url": hit["u"]}
    return out


def table_rows(t):
    """'| MODEL | Ver.2.7 | Apr. 25, 2022 |' or '| MODEL | 1.9 | Click here | Nov. 04, 2025 |' -> {norm(model): (ver, date)}"""
    rows = {}
    for m in re.finditer(r"\|\s*([A-Za-z][\w./ -]{1,60}?)\s*\|\s*(?:Ver\.)?\s*(\d+\.\d+)\s*\|\s*(?:Click here\s*\|\s*)?([A-Z][a-z]{2}\.?\s*\d{1,2},\s*\d{4})", t):
        d = mdy(m[3])
        if d:
            for name in m[1].split("/"):
                rows.setdefault(norm(name), (m[2], d, m[1]))
    return rows


def panasonic(models):
    base = "https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/"
    rows = {}
    for page in ("index.html", "index4.html"):
        for n, (v, d, _) in table_rows(text(get(base + page))).items():
            rows.setdefault(n, (v, d, base + page))
    out = {}
    for k, mo in models.items():
        if mo["brand"] != "Panasonic" or mo["category"] != "camera":
            continue
        m = mo["name"].replace("Panasonic ", "").replace(" II", "M2").replace(" ", "")
        for pre in ("dc", "dmc"):
            hit = rows.get(norm(pre + m))
            if hit:
                out[k] = {"version": hit[0], "released": hit[1], "url": hit[2]}
                break
    return out


def omsystem(models):
    url = "https://support.jp.omsystem.com/en/support/imsg/digicamera/download/software/firm/e1/"
    rows = table_rows(text(get(url)))
    lens_c = [(s[0], s[1], s[2], {"v": v, "d": d}) for n, (v, d, name) in rows.items() if "zuiko" in n and (s := lens_sig(name.replace(" F", " f/")))]
    out = {}
    for k, mo in models.items():
        if mo["brand"] not in ("OM System", "Olympus"):
            continue
        if mo["category"] == "camera":
            if mo["brand"] == "Olympus" and re.match(r"Olympus OM\d", mo["name"]):
                continue  # Olympus OM-1/OM-3 are film SLRs; the digital ones are OM System
            n = mo["name"].split(" ", 1 if mo["brand"] == "Olympus" else 2)[-1]
            n = re.sub(r"^(E|OM)(?=M?\d)", r"\1-", n.replace("EM", "E-M").replace("EP", "E-P")).replace(" II", " Mark II").replace(" III", " Mark III")
            hit = rows.get(norm(n))
            hit = hit and {"v": hit[0], "d": hit[1]}
        elif mo["category"] == "lens" and mo["mount"] == "Micro Four Thirds":
            hit = match_lens(lens_sig(mo["name"]), lens_c)
        else:
            continue
        if hit:
            out[k] = {"version": hit["v"], "released": hit["d"], "url": url}
    return out


RICOH = {"camera-pentax-k1": "k1.html", "camera-pentax-k5-ii": "k-5_2_s.html", "camera-pentax-k7": "k-7_s.html",
         "camera-ricoh-gr": "gr_s.html", "camera-ricoh-griii": "gr3_s.html", "camera-ricoh-griiix": "gr3x_s.html", "camera-ricoh-griv": "gr4_s.html"}


def ricoh(models):
    out = {}
    for k, page in RICOH.items():
        if k not in models:
            continue
        url = "https://www.ricoh-imaging.co.jp/english/support/digital/" + page
        h = get(url)
        t = text(h)
        v = re.search(r"Software Version\s*(\d+\.\d+)", t)
        d = re.search(r"\b(20\d\d)/(\d\d)/(\d\d)\b", h)
        if v and d:
            out[k] = {"version": v[1], "released": f"{d[1]}-{d[2]}-{d[3]}", "url": url}
    return out


def main():
    models = json.loads((ROOT / "data" / "models.json").read_text())
    old = json.loads(OUT.read_text()).get("models", {}) if OUT.exists() else {}
    today = dt.date.today().isoformat()
    new = {}
    for name, fn in [("Fujifilm", fujifilm), ("Nikon", nikon), ("Panasonic", panasonic), ("OM System", omsystem), ("Ricoh", ricoh)]:
        got = fn(models)
        print(f"{name}: {len(got)}")
        for k, e in got.items():
            e["checked"] = today
            o = old.get(k, {})
            if o.get("attention") and o.get("version") == e["version"]:  # keep a curated note only for the same release
                e["attention"], e["attention_source"] = o["attention"], o.get("attention_source")
            new[k] = e
    for k, o in old.items():  # keep models no longer in today's models.json (pages may come back)
        new.setdefault(k, o)
    doc = {"_about": "Latest firmware per model from manufacturers' official pages. Refresh: python3 scripts/firmware.py",
           "updated": today, "models": dict(sorted(new.items()))}
    if "--dry-run" in sys.argv:
        print(json.dumps(doc, indent=1)[:3000])
    else:
        OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        print(f"wrote {OUT} ({len(new)} models)")


if __name__ == "__main__":
    main()
