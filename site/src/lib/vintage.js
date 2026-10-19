// Vintage & Thrift Finds classifier (/vintage/). Mount tags plus title keywords, tuned for precision:
// when a title could be digital, it's left out. Pure functions so tests/test_vintage.mjs can check real titles.

export const GROUPS = [
  { id: 'film35', name: 'Film SLRs & rangefinders', blurb: '35mm bodies: manual and early-autofocus SLRs, rangefinders.' },
  { id: 'filmmf', name: 'Medium & large format film', blurb: 'TLRs, 645/6x6/6x7 systems, field and view cameras.' },
  { id: 'compact', name: 'Film compacts & point-and-shoots', blurb: 'Pocketable 35mm (and smaller) film cameras.' },
  { id: 'instant', name: 'Instant cameras', blurb: 'Instant film cameras (check the film type is still made).' },
  { id: 'lens', name: 'Vintage manual-focus lenses', blurb: 'Manual-focus lenses from film-era mounts. Most adapt to mirrorless bodies.' },
];

const t = (s) => ' ' + String(s || '').toLowerCase().replace(/[‘’]/g, "'") + ' ';
const any = (s, res) => res.some((r) => r.test(s));

// Anything that says it's digital (or an accessory) is never a film camera.
const DIGITAL = [/dzofilm|\bcine\b|\bsigma fp\b|645 ?z\b|645 ?d\b|digital|numérique|mirrorless|dslr|megapixel|\b\d+(\.\d+)?\s?mp\b|\b4k\b|wi-?fi|\bevf\b|camcorder|handycam|video|cinema|\bccd\b|\bcmos\b|powershot|coolpix|cyber-?shot|lumix|finepix|exilim|easyshare|optio|\bixus\b|\belph\b|\bdmc-|\bdsc-|instax (mini )?(link|evo)|theta|gopro|osmo|\bgfx|x100|\bricoh gr ?(ii|iii|iv|3|4)|\bgr ?iii|\bq2\b|\bq3\b|rx1|rx10|rx100|\btg-?\d|\bnex-|\bzv-?e|\bfx-?30/];
const STRONG_ACC = /\badapt|adaptateur|\bcap\b|\bcaps\b|\bhood|\bshade\b|\bfilter|converter|correction lens|eyepiece|focabell|visoflex|\bshoe\b|\bhandle\b|power ?grip|\bgrip\b|\bcrystal\b|replica|dummy|\b120 back|\bfilm back|\bback only/;
const ACCESSORY = [/\badapt|adaptateur|\bcap\b|\bcaps\b|hood|shade|\bfilter|strap|\bcase\b|\bbag\b|screen|eyepiece|\bgrip\b|winder|motor drive|battery|charger|flash|bellows|extension tube|teleconverter|converter|\bring\b|insert|back only|film back|viewfinder|finder|prism|bracket|manual|instruction|\bbox only|focabell|visoflex|\bcable|release|remote/];

const FILM_ONLY_MOUNTS = new Set(['Canon FD', 'Minolta MD', 'M42', 'Olympus OM', 'Contax/Yashica', 'Konica AR', 'Leica R', 'Contax N']);
const MF_FILM_MOUNTS = new Set(['Mamiya RB/RZ', 'Mamiya 7', 'Hasselblad V', 'Bronica SQ', 'Bronica GS', 'Pentax 67', 'Large Format', 'Hasselblad XPan']);
const MF_MAYBE_DIGITAL = new Set(['Mamiya 645', 'Pentax 645']); // 645D/645Z/ZD are digital

// Film bodies on mounts that also have digital bodies (word-boundary keyword lists).
const FILM_BODY_KEYWORDS = [
  // Nikon F mount film bodies
  /\bnikon (f|f2|f3|f4|f5|f6|f100|f80|f75|f65|f60|f70|f90x?|f801s?|f601|f401s?|fm|fm2n?|fm3a|fm10|fe|fe2|fe10|fa|fg|fg-20|em)\b/, /\bnikkormat\b/, /\bnikon n\d{2,4}s?\b/, /\bnikon f photomic\b/, /\bnikonos\b/,
  // Pentax K film bodies
  /\bpentax (k1000|kx|km|k2|me|me super|mx|mv|lx|p30t?|p3|program a|super program|super a|a3|sf-?1n?|sf10|sfxn?|pz-?\d|zx-?\d+|mz-?\d+|\*ist(?! d))\b/,
  // Canon EF film bodies
  /\bcanon (eos )?(elan|rebel (x|xs|g|g ii|k2|ti|2000|t2)|a2e?|eos-?1n|eos-?1v|eos 3|eos 5|eos 500n?|eos 300|eos 3000|620|630|650|700|750|850|ef-m 35mm film)\b/, /\bcanon (700|750) w\//,
  // Minolta / Sony A mount film bodies
  /\bminolta (maxxum|dynax|alpha|\d{1,2}xi|7xi|9xi|5xi|3xi|7000|9000|5000|xd|xg|x-?700|x-?570|x-?370|srt|sr-?t|xe|hi-matic|cle)\b/, /\bminolta (7s|super a)\b/,
  // Leica M film bodies
  /\bleica (m2|m3|m4|m4-2|m4-p|m5|m6|m7|mp|m-a|cl|minilux|mini|cm|iii[a-g]?|ii[a-f]?|if|ic)\b/,
  // generic film cues
  /\b35\s?mm (film|slr|rangefinder)|\bfilm (camera|slr)|\bargentique|\brangefinder\b|\bslr camera\b/,
  /\b(voigtlander|voigtländer) (prominent|vito|bessa|vitessa|bessamatic)\b/, /\bfed-?\d|\bzorki\b|\bkiev\b|\bpraktica\b|\bexakta\b|\bminox\b|\bpellix\b|\bicarex\b|\brollei sl35|\brolleiflex sl35|\bkowa (r2|six|se)\b|\byashica (fx|electro|200af|lynx|minister)\b|\bvivitar v\d{4}/, /\bsigma (sa-|bf)/, /\bpetri\b|\bhexar rf\b|\bcontax (g1|g2|rx|rts|167mt|aria|s2)\b/,
];
const MF_KEYWORDS = [/\b(tlr|rolleiflex|rolleicord|yashica-?mat|yashica 124|mamiya c\d{2,3}[sf]*|seagull|lubitel|hasselblad (500|501|503|553|201|203|205|swc|903)|bronica|mamiya (6|7)\b|mamiya rb|mamiya rz|pentax 67|pentax 6x7|fuji(film)? (ga|gw|gsw|gf|gs)\d{3}|4x5|8x10|field camera|view camera|technical camera|tachihara|wista|wisner|zone vi|toyo|graflex|speed graphic|linhof|chamonix|intrepid|horseman|nagaoka|holga|diana)\b/];
const COMPACT_KEYWORDS = [
  /\bolympus (stylus epic|stylus zoom|stylus 35|mju[- ]?(ii|i|zoom)?|infinity|xa\d?|trip 35|35 ?rc|35 ?sp|pen (ee|ees|ee-?\d|d|f|ft|s))\b/,
  /\b(yashica|kyocera) (t\d|t4|t5|t3|t2|samurai|electro 35|mf-?\d)\b/, /\bcontax (t|t2|t3|tvs|tix)\b/, /\bnikon (l35af|l35|28ti|35ti|lite ?touch|one ?touch|zoom ?touch|af600)\b/,
  /\bcanon (sure ?shot|af35m|autoboy|prima|canonet|ql17|snappy|owl|a35|af-?7)\b/, /\bminolta (riva|freedom|af-?c|af-?s|tc-?1|prod)\b/, /\bpentax (espio|iqzoom|pc-?35|zoom 70|uc-?1|mx-?1(?!0))\b/,
  /\bricoh (gr1v?s?|gr10|gr21|ff-?\d|r1|500 ?g)\b/, /\bkonica (big mini|c35|hexar af|pop|z-up|mg)\b/, /\brollei (35|prego)\b/, /\bfuji(film)? (klasse|natura|dl-?\d|tiara|silvi|zoom date)\b/,
  /\blomo (lc-?a|lc-wide|lomo)\b|\bsubminiature\b|\bhit type\b|\bhalf-?frame\b|\bpoint (and|&) shoot\b|\bkodak (ektar h35|retina|instamatic|brownie)\b/,
];
const INSTANT_KEYWORDS = [/\bpolaroid\b|\binstax\b(?! (mini )?(link|evo))|\binstant (camera|wide|film)\b|lomo instant|\bnons sl\d|\bmint (tl70|instantkon)|\bsx-?70\b|\bland camera\b|\bspectra\b|\bone ?step\b/];

// Lens rules
const VINTAGE_LENS_MOUNTS = new Set(['M42', 'Canon FD', 'Minolta MD', 'Olympus OM', 'Contax/Yashica', 'Konica AR', 'Leica R']);
const AF_MARKERS = [/\baf\b|af-s|afs\b|af-d|af-p|af-i|\bvr\b|\bdx\b|\bed if af|\bg ed\b|\d\.?\d?g\b|\bfa\b|\bd fa\b|\bda\b|\bda\*|\bdal?\b|\bdc\b|\bhsm\b|\bsdm\b|\bwr\b|\bstm\b|\busm\b|\bdi\b|\bvc\b|\bos\b|\bex dg\b|\bart\b|\bcontemporary\b|\bsports\b|\bz ?\d|milvus|\bzf\.2|\bze\b|\bm\.zuiko/];
const DIGITAL_MOUNTS = new Set(['Sony E', 'Fujifilm X', 'Nikon Z', 'Canon RF', 'L-Mount', 'Micro Four Thirds', 'Canon EF-M', 'Fujifilm G', 'Hasselblad XCD', 'Hasselblad H', 'Four Thirds']);
const MODERN_MANUAL = /laowa|thypoch|typoch|tt ?artisan|7 ?artisans|light lens lab|voigtl|\bzm\b|biogon m-mount|samyang|rokinon|meike|viltrox|sirui|irix|mitakon|zhongyi|kipon|brightin|pergear|funleader/;
function looksLikeBody(s) { return /\bcamera\b|\bbody\b|\bslr\b|sensorex|\bw\/\d|super program/.test(s) && !/\blens for\b|used lens/.test(s); }
const NIKON_MANUAL = [/\bai-?s\b|\bais\b|\bai\b|\bpre-?ai\b|\bnon-?ai\b|\bnikkor-?[ohspqnu]\b|\bnikkor-[a-z]\.?c\b|\bseries e\b|\bauto nikkor\b|\bnikkor-?h auto/];
const PENTAX_MANUAL = [/\bsmc\b|\btakumar|\bpentax-?a\b|\bpentax-?m\b|\bk mount\b|\bpk-?a\b|\bsemi-auto/];
const LTM_WORDS = [/\bltm\b|\bm39\b|leica thread|screw mount|\bexakta\b|\bcanon fl\b|\bpraktica\b|\btopcon\b|\bmiranda\b|\brokkor\b|\bzuiko auto\b|\btakumar\b|\bhelios\b|\bjupiter-?\d|\bindustar\b|\bmir-?\d/];

export function classify(l) {
  if (!l || l.price_cad == null) return null;
  const s = t(l.title), m = l.mount, c = l.category;
  if (c === 'camera' || (c === 'lens' && looksLikeBody(s))) {
    if (any(s, DIGITAL)) return null;
    if (STRONG_ACC.test(s) && !/\bcamera\b|\bw\/|\bwith\b/.test(s)) return null;
    if (c === 'camera' && /\blens\b/.test(s) && !/\bcamera\b|\bw\/|\bwith\b|\bbody\b/.test(s)) return /\d/.test(s) ? 'lens' : null;
    if (any(s, INSTANT_KEYWORDS)) return 'instant';
    if (any(s, ACCESSORY) && !/\bw\/|with\b/.test(s)) return null;
    if (DIGITAL_MOUNTS.has(m)) return null;
    if (/\bsl35\b/.test(s)) return 'film35';
    if (MF_FILM_MOUNTS.has(m) || any(s, MF_KEYWORDS)) return /\bcfv\b|\bdigital back|\bphase one|\bleaf\b|\bcredo\b/.test(s) ? null : 'filmmf';
    if (MF_MAYBE_DIGITAL.has(m)) return /645 ?(d|z)\b|\bzd\b|\bdf\+?|\biq\d/.test(s) ? null : 'filmmf';
    if (any(s, COMPACT_KEYWORDS)) return 'compact';
    if (FILM_ONLY_MOUNTS.has(m)) return 'film35';
    if (any(s, FILM_BODY_KEYWORDS)) return 'film35';
    if (c === 'lens') return 'film35'; // a body listed under lenses (e.g. "Miranda Sensorex w/50mm")
    return null;
  }
  if (c === 'lens') {
    if (STRONG_ACC.test(s) || /\bbellows\b(?!.*\d+\s?mm)/.test(s)) return null;
    if (!/\d/.test(s) || MODERN_MANUAL.test(s)) return null;
    if (VINTAGE_LENS_MOUNTS.has(m)) return /\beos\b|\bfor (nikon|canon ef|sony|fuji)|\bzf\.2|\bmilvus|tamron 28-[23]00|at-x/.test(s) ? null : 'lens';
    if (m === 'Leica M') return /\basph/.test(s) ? null : 'lens';
    if (m === 'Nikon F') return any(s, NIKON_MANUAL) && !any(s, AF_MARKERS) ? 'lens' : null;
    if (m === 'Pentax K') {
      const manual = any(s, PENTAX_MANUAL) || (/\bk mount|\bp\/?k\b/.test(s) && /vivitar|soligor|rikenon|panagor|kiron|hanimex|\bimage\b|\brmc\b|sears|makinon|cosina|takumar/.test(s));
      return manual && !any(s, AF_MARKERS) && !/\b6x7|\b67\b|645|\b110\b|limited|pentax[- ]f\b|\bf smc/.test(s) ? 'lens' : null;
    }
    if (!m && any(s, LTM_WORDS) && !any(s, AF_MARKERS)) return 'lens';
    return null;
  }
  return null;
}

export function vintageGroups(listings) {
  const out = Object.fromEntries(GROUPS.map((g) => [g.id, []]));
  for (const l of listings) { const g = classify(l); if (g) out[g].push(l); }
  const key = (l) => [l.deal_score == null ? -1 : l.deal_score, -l.price_cad];
  for (const g of Object.values(out)) g.sort((a, b) => { const [sa, pa] = key(a), [sb, pb] = key(b); return sb - sa || pb - pa; });
  return out;
}
