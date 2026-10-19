// "Can I make this work with my camera?" logic for /adapt/. Pure functions, used at build time
// (classifying adapter listings) and in the browser (verdicts). Mount numbers live in data/mounts.json.

// Adapters known to keep autofocus / electronic aperture for a lens>body pair. General guidance only:
// support varies by lens and firmware, so the page always says to check the adapter maker's list.
export const AF_ADAPTERS = {
  'Canon EF>Canon RF': "Canon Mount Adapter EF-EOS R (first-party, full autofocus and stabilisation)",
  'Canon EF>Canon EF-M': "Canon Mount Adapter EF-EOS M (first-party, full autofocus)",
  'Nikon F>Nikon Z': "Nikon FTZ / FTZ II (first-party; autofocus with AF-S, AF-P and E lenses, manual focus with screw-drive AF/AF-D lenses)",
  'Sony A>Sony E': "Sony LA-EA3 / LA-EA5 (first-party; LA-EA5 adds screw-drive autofocus on some bodies)",
  'Four Thirds>Micro Four Thirds': "OM/Olympus MMF-2/MMF-3 or Panasonic DMW-MA1 (first-party, autofocus)",
  'Canon EF>Sony E': "Sigma MC-11, Metabones Smart Adapter, Viltrox EF-E (autofocus, speed varies by lens)",
  'Canon EF>L-Mount': "Sigma MC-21 (autofocus with supported lenses)",
  'Canon EF>Fujifilm X': "Fringer EF-FX Pro, Viltrox EF-FX (autofocus, speed varies)",
  'Canon EF>Micro Four Thirds': "Metabones, Viltrox EF-M1/EF-M2 (autofocus with many lenses)",
  'Canon EF>Nikon Z': "Megadap EFTZ, Commlite CM-EF-NZ (autofocus with many lenses)",
  'Canon EF>Fujifilm G': "Fringer EF-GFX (autofocus; lenses designed for 35 mm may vignette)",
  'Nikon F>Sony E': "Commlite CM-ENF-E1 Pro, Megadap (autofocus with AF-S/AF-P lenses)",
  'Sony E>Nikon Z': "Megadap ETZ21, Techart TZE-01 (autofocus with many lenses)",
  'Leica M>Sony E': "Techart LM-EA9 (adds autofocus to manual M lenses)",
  'Leica M>Nikon Z': "Techart TZM-02, Megadap MTZ11 (adds autofocus to manual M lenses)",
  'Fujifilm X>Fujifilm G': "Fringer FR-FTG1 (autofocus; crop mode needed on GFX)",
  'M42>Pentax K': "Pentax Adapter K for M42 (sits inside the mount; manual stop-down metering)",
};

const FORMAT_RANK = { mft: 1, apsc: 2, ff: 3, mf: 4, '6x7': 5 };
const FORMAT_NAME = { mft: 'Four Thirds-size', apsc: 'APS-C', ff: 'full-frame (35 mm)', mf: 'medium format', '6x7': '6×7 medium format' };

// Returns { verdict: 'native'|'adapter'|'limits'|'impossible'|'unknown', title, notes: [], gap }
export function verdict(lensMount, bodyMount, mounts, opts = {}) {
  const L = mounts[lensMount], B = mounts[bodyMount];
  if (lensMount === 'Fixed Lens' || bodyMount === 'Fixed Lens') return { verdict: 'impossible', title: "Can't work: the lens is built into the camera", notes: ['Fixed-lens cameras have no removable mount, so nothing can be swapped on or off.'] };
  if (!L || !B) return { verdict: 'unknown', title: "We don't have data for this mount yet", notes: [] };
  const notes = [];
  const lf = FORMAT_RANK[opts.lensFormat || L.format] || 3, bf = FORMAT_RANK[B.format] || 3;
  const coverage = () => {
    if (lf < bf) notes.push(`The lens is made for a smaller ${FORMAT_NAME[opts.lensFormat || L.format]} image, so expect dark corners on this ${FORMAT_NAME[B.format]} body unless you use crop mode.`);
    else if (lf > bf) notes.push(`The lens covers a bigger image than this ${FORMAT_NAME[B.format]} sensor, so you see a crop of it (a narrower field of view). That's fine, and often sharp.`);
  };
  if (lensMount === bodyMount) {
    coverage();
    return { verdict: 'native', title: 'Fits natively, no adapter needed', notes, gap: 0 };
  }
  const gap = Math.round((L.flange_mm - B.flange_mm) * 100) / 100;
  const af = AF_ADAPTERS[`${lensMount}>${bodyMount}`];
  if (gap < 0 && !af) {
    notes.push(`${lensMount} lenses sit ${L.flange_mm} mm from the sensor, but a ${bodyMount} body needs ${B.flange_mm} mm, so the lens would end up ${Math.abs(gap)} mm too far away and can't focus to infinity.`);
    notes.push('Adapters with a glass element exist for some pairs, but they act like a weak teleconverter and soften the image. Without glass it only works for close-up and macro work.');
    return { verdict: 'impossible', title: "Can't work properly: no room for an adapter", notes, gap };
  }
  if (af) notes.push(`Adapter that keeps electronics: ${af}. Check the adapter maker's compatibility list for your exact lens.`);
  let limits = false;
  if (!af && gap < 1) { limits = true; notes.push(`Only ${gap} mm of room for an adapter, so it has to be very thin or sit inside the mount. Few exist; check before buying.`); }
  if (!af) {
    if (L.aperture === 'electronic') { limits = true; notes.push(`${lensMount} lenses set aperture electronically. A plain adapter can't control it, so you'd be stuck wide open unless you buy an electronic adapter.`); }
    else if (L.aperture === 'mixed') notes.push(`Older ${lensMount} lenses with an aperture ring adapt easily. Lenses without one need an adapter with an aperture control lever.`);
    notes.push(B.type === 'mirrorless' ? 'Plain adapters are manual focus. Most mirrorless bodies have focus peaking and magnification, which makes this easy.' : 'Plain adapters are manual focus.');
    if (B.type === 'rangefinder') { limits = true; notes.push(`The ${bodyMount} rangefinder won't couple to an adapted lens, so you focus by scale (or with live view on digital bodies).`); }
    else if (B.type !== 'mirrorless') { limits = true; notes.push(`On a ${bodyMount} SLR or DSLR you lose the lens's aperture linkage, so metering is stop-down.`); }
  }
  if (B.type === 'slr' && L.type !== 'slr' && !af) limits = true;
  if (L.type === 'rangefinder' && B.type === 'slr') {
    return { verdict: 'impossible', title: "Can't work properly: rangefinder lenses sit too close", notes: [`${lensMount} lenses need to sit ${L.flange_mm} mm from the film or sensor, closer than a ${bodyMount} body's mirror box allows.`], gap };
  }
  coverage();
  if (lf < bf) limits = true;
  return limits
    ? { verdict: 'limits', title: 'Works with an adapter, with catches', notes, gap }
    : { verdict: 'adapter', title: 'Works with an adapter', notes, gap };
}

// ---------- build time: classify our adapter listings into lens>body pairs ----------
export const ADAPTER_BRANDS = ['Promaster', 'Pholsy', 'Voigtlander', 'Metabones', 'Viltrox', 'Fringer', 'Sigma', 'Canon', 'Nikon', 'Sony', 'Fotodiox', 'K&F Concept', 'Urth', 'Kipon', 'Novoflex', 'Techart', 'Megadap', 'Commlite', 'Pentax', 'Olympus', 'Panasonic', 'Kiwi', 'Beschoi'];
const BRAND_RX = [['K&F Concept', /k\s?&\s?f/i], ['Commlite', /c?ommlite/i], ['Sigma', /\bsigma\b|\bmc-?(11|21)\b/i]];

const MOUNT_RX = [
  ['Hasselblad XCD', /\bxcd\b|hasselblad x(?![a-z])|x-?system/i],
  ['Hasselblad V', /\bhasselblad\b(?! x)|\bhassy\b|(?<=x-)v\b/i],
  ['Fujifilm G', /\bgfx\b|\bg-?mount\b/i],
  ['Micro Four Thirds', /\bm\s?4\/3\b|\bmft\b|micro\s?(four thirds|4\/3)|\bm43\b/i],
  ['Four Thirds', /(?<!micro\s?)(?<!m\s?)\b(four thirds|4\/3)\b/i],
  ['Canon EF-M', /\bef-?m\b|\beos[- ]?m\b/i],
  ['Canon RF', /\brf\b|\beos[- ]?r\b/i],
  ['Canon FD', /\bfd\b/i],
  ['Canon EF', /\bef\b(?!-?[ms]\b)|\beos\b(?![- ]?[mr]\b)|canon\s?ef/i],
  ['Nikon Z', /\bnik(on)?\s?z\b|\bnz\b|\bz[- ]?mount\b|\bftz\b/i],
  ['Nikon F', /\bnik(on)?\b(?!\s?z)|\bf[- ]?mount\b/i],
  ['Sony A', /\bsony\s?a\b|\ba-?mount\b|\bmaxxum\b|\bla-ea/i],
  ['Sony E', /\bnex\b|\be-?mount\b|\bsony\s?(fe|e)\b|\bfe\b|[-/>]\s?e\b/i],
  ['Fujifilm X', /\bfx\b|\bxf\b|fuji(film)?\s?x\b|\bx-?mount\b|\bfux\b|\bfuji\b/i],
  ['L-Mount', /\bl-?mount\b|\bleica\s?(sl|l)\b|\bmc-21\b|[-/>]\s?l\b(?!\/)/i],
  ['Leica R', /\bleica\s?r\b|\blr\b/i],
  ['Leica M', /\bleica\s?m\b|\bl\/m\b|\blm\b|\bm-?mount\b|\bleica\b(?!\s?[rl]\b|\s?sl\b)/i],
  ['M42', /\bm42\b/i],
  ['Pentax K', /\bpentax\s?k\b|\bpk\b|\bk-?mount\b|-k\b/i],
  ['Minolta MD', /\bmc\/md\b|\bmd\b|\bminolta\b(?!\s?a\b)/i],
  ['Olympus OM', /\bolympus\s?om\b|\bom\b/i],
  ['Contax/Yashica', /\bc\/y\b|\bcontax\b(?!\s?n\b)|\byashica\b|\bcy\b/i],
  ['Mamiya 645', /mamiya\s?645|\bm645\b/i],
  ['Mamiya RB/RZ', /\brb67\b|\brz67\b|mamiya\s?r[bz]/i],
];
const NAMED = [
  [/ef-?eos\s?r\b/i, 'Canon EF', 'Canon RF'], [/ef-?eos\s?m\b/i, 'Canon EF', 'Canon EF-M'], [/\bftz\b/i, 'Nikon F', 'Nikon Z'],
  [/\bmc-?11\b/i, 'Canon EF', 'Sony E'], [/\bmc-?21\b/i, 'Canon EF', 'L-Mount'], [/\bla-ea\d/i, 'Sony A', 'Sony E'],
  [/\bmmf-?\d\b|dmw-ma1/i, 'Four Thirds', 'Micro Four Thirds'], [/hasselblad x-?v\b/i, 'Hasselblad V', 'Hasselblad XCD'],
];
const ADAPTER_ONLY_BRANDS = /metabones|fringer|megadap|techart|urth|fotodiox|k\s?&\s?f|c?ommlite|novoflex/i;
const IS_ADAPTER = /adapt|\bftz\b|\bmc-?(11|21)\b|\bla-ea\d|\bmmf-?\d|->|\bto\b|\bà\b/i;
const NOT_MOUNT_ADAPTER = /\b(ac|power|flash|shoe|filter|ring|rings|cable|cord|remote|gps|tripod|quick release|bellows|macro|stereo|panoramic|wcl|wireless|battery|teleconverter|converter lens|ext(ension)? tube|series \d|collar|bracket|visoflex|photar|cx|vr-pro|digital adapter|board|lens adapter for|retaining|switch|lever)\b|dmw-la|tc-|la-dc/i;

export function brandOf(title) {
  for (const [b, rx] of BRAND_RX) if (rx.test(title)) return b;
  const t = title.toLowerCase();
  let best = '', at = Infinity;
  for (const b of ADAPTER_BRANDS) { const i = t.indexOf(b.toLowerCase()); if (i >= 0 && i < at) { at = i; best = b; } }
  return best;
}

// Returns {from, to} or null. Order in the title decides direction ("Leica M to Sony E", "EF-E", "Nikon -> Canon EF").
export function classifyAdapter(title) {
  const t = String(title || '').replace(/\(.*?\)|\*.*?\*|\[.*?\]/g, ' ');
  if (!(IS_ADAPTER.test(t) || ADAPTER_ONLY_BRANDS.test(t)) || NOT_MOUNT_ADAPTER.test(t)) return null;
  for (const [rx, from, to] of NAMED) if (rx.test(t)) return { from, to };
  // Novoflex names adapters BODY/LENS (e.g. "EOS/NIK" = Nikon F lens on a Canon EF body).
  const novoSwap = /novoflex/i.test(t) && /\b[a-z]{2,5}\/[a-z]{2,5}\b/i.test(t) && !/->|\bto\b/i.test(t);
  let s = t.replace(/\b(adapter|adaptateur|mount|lens|used|pro|smart|speed booster|ultra|ii|iv|iii|af|for|à|to)\b/gi, (m) => (/^(to|à)$/i.test(m) ? ' > ' : ' '));
  const hits = [];
  for (const [name, rx] of MOUNT_RX) {
    const g = new RegExp(rx.source, 'ig');
    let m;
    while ((m = g.exec(s))) { hits.push({ name, at: m.index, len: m[0].length }); if (!m[0].length) g.lastIndex++; }
  }
  // keep earliest non-overlapping hits; one per mount
  hits.sort((a, b) => a.at - b.at || b.len - a.len);
  const seen = new Set(), ordered = [];
  let end = -1;
  for (const h of hits) { if (h.at < end || seen.has(h.name)) continue; seen.add(h.name); ordered.push(h.name); end = h.at + h.len; }
  if (ordered.length !== 2) return null;
  return novoSwap ? { from: ordered[1], to: ordered[0] } : { from: ordered[0], to: ordered[1] };
}

export function conditionOf(l) {
  if (/\bnew\b|new in box|\bnos\b/i.test(l.title) && !/\bused\b/i.test(l.title)) return 'New';
  if (l.condition || /\bused\b/i.test(l.title)) return 'Used';
  return 'Condition not stated';
}
