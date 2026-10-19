// "My kit" core: lists stored in this browser only (localStorage), share-link encoding,
// simple mount-compatibility rules and kit totals. No network calls except our own /kit-data.json.
// Pure functions are exported for tests (tests/mykit.test.mjs).

export const STORE_KEY = 'ug.lists.v1';
export const MAX_LISTS = 30;
export const MAX_ITEMS = 200;

export const CATEGORIES = [
  ['body', 'Camera body'],
  ['film', 'Film camera'],
  ['lens', 'Lens'],
  ['flash', 'Flash / lighting'],
  ['support', 'Tripod / support'],
  ['audio', 'Audio'],
  ['bag', 'Bag / strap'],
  ['acc', 'Accessory'],
  ['other', 'Other'],
];
export const CAT_LABEL = Object.fromEntries(CATEGORIES);
export const CAT_PLURAL = { body: 'Bodies', film: 'Film cameras', lens: 'Lenses', flash: 'Lighting', support: 'Support', audio: 'Audio', bag: 'Bags', acc: 'Accessories', other: 'Other' };
const CAT_ORDER = CATEGORIES.map((c) => c[0]);
export const isBodyCat = (c) => c === 'body' || c === 'film';

// Mounts we only see on film-era cameras: a "camera" model on one of these defaults to the Film camera category.
const FILM_MOUNTS = new Set(['Canon FD', 'Minolta MD', 'M42', 'Olympus OM', 'Contax/Yashica', 'Konica AR', 'Leica R', 'Mamiya 645', 'Mamiya RB/RZ', 'Mamiya 7', 'Hasselblad V', 'Bronica SQ', 'Bronica GS', 'Pentax 67', 'Pentax 645', 'Large Format', 'Hasselblad XPan', 'Contax N']);
export function defaultCat(modelCategory, mount, key = '') {
  if (modelCategory === 'lens' || String(key).startsWith('lens-')) return 'lens';
  if (modelCategory === 'camera' || String(key).startsWith('camera-')) return FILM_MOUNTS.has(mount) ? 'film' : 'body';
  return 'other';
}

// ---------- sanitising (imports and share links are untrusted input) ----------
const str = (v, n = 160) => (typeof v === 'string' ? v.replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, n) : '');
const num = (v) => { const x = Number(v); return Number.isFinite(x) && x > 0 && x < 1e7 ? Math.round(x * 100) / 100 : null; };
const uid = () => Math.random().toString(36).slice(2, 10);

export function cleanItem(it) {
  if (!it || typeof it !== 'object') return null;
  const k = str(it.k, 120).replace(/[^a-z0-9_\-]/gi, '');
  const n = str(it.n, 160);
  if (!k && !n) return null;
  const c = CAT_LABEL[it.c] ? it.c : defaultCat('', '', k);
  return { k: k || null, n: n || k, c, m: str(it.m, 40) || null, t: num(it.t) };
}
export function cleanList(l) {
  if (!l || typeof l !== 'object') return null;
  const items = (Array.isArray(l.items) ? l.items : []).map(cleanItem).filter(Boolean).slice(0, MAX_ITEMS);
  const kind = ['wish', 'own', 'kit'].includes(l.kind) ? l.kind : 'kit';
  return { id: str(l.id, 20).replace(/[^a-z0-9]/gi, '') || uid(), name: str(l.name, 60) || 'My list', kind, items };
}
export function cleanState(s) {
  const lists = (s && Array.isArray(s.lists) ? s.lists : []).map(cleanList).filter(Boolean).slice(0, MAX_LISTS);
  const ids = new Set();
  for (const l of lists) { while (ids.has(l.id)) l.id = uid(); ids.add(l.id); }
  return { v: 1, active: lists.some((l) => l.id === s?.active) ? s.active : lists[0]?.id || null, lists, profile: { handle: str(s?.profile?.handle, 40) } };
}
export function defaultState() {
  return { v: 1, active: 'wish', lists: [
    { id: 'wish', name: 'Wish list', kind: 'wish', items: [] },
    { id: 'own', name: 'What I own', kind: 'own', items: [] },
  ], profile: { handle: '' } };
}

// ---------- storage ----------
export function load() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return defaultState();
    const s = cleanState(JSON.parse(raw));
    return s.lists.length ? s : defaultState();
  } catch { return defaultState(); }
}
export function save(s) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(cleanState(s))); } catch {}
  try { window.dispatchEvent(new CustomEvent('ug:lists')); } catch {}
}
export const newList = (name, kind = 'kit', items = []) => ({ id: uid(), name: str(name, 60) || 'New kit', kind, items });
export function wishList(s) {
  let l = s.lists.find((x) => x.kind === 'wish');
  if (!l) { l = { id: uid(), name: 'Wish list', kind: 'wish', items: [] }; s.lists.unshift(l); }
  return l;
}
export function uniqueName(s, name) {
  const names = new Set(s.lists.map((l) => l.name));
  if (!names.has(name)) return name;
  for (let i = 2; ; i++) if (!names.has(`${name} (${i})`)) return `${name} (${i})`;
}

// ---------- share links: /kit/#z<base64url(deflate-raw(json))> (or #j<base64url(json)> without CompressionStream) ----------
const b64u = (bytes) => { let s = ''; for (const b of bytes) s += String.fromCharCode(b); return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, ''); };
const unb64u = (t) => { const s = atob(t.replace(/-/g, '+').replace(/_/g, '/')); return Uint8Array.from(s, (c) => c.charCodeAt(0)); };
async function pipe(bytes, stream) { return new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(stream)).arrayBuffer()); }

export function packList(list, handle = '') {
  const o = { v: 1, n: list.name, i: list.items.map((it) => [it.k || '', it.k ? '' : it.n, it.c, it.m && !it.k ? it.m : '', it.t || 0]) };
  if (handle) o.h = handle;
  return o;
}
export function unpackList(o) {
  if (!o || typeof o !== 'object' || !Array.isArray(o.i)) throw new Error('bad kit');
  const items = o.i.slice(0, MAX_ITEMS).map((a) => cleanItem(Array.isArray(a) ? { k: a[0], n: a[1] || a[0], c: a[2], m: a[3], t: a[4] } : null)).filter(Boolean);
  return { name: str(o.n, 60) || 'Shared kit', handle: str(o.h, 40), items };
}
export async function encodeList(list, handle = '') {
  const bytes = new TextEncoder().encode(JSON.stringify(packList(list, handle)));
  if (typeof CompressionStream !== 'undefined') return 'z' + b64u(await pipe(bytes, new CompressionStream('deflate-raw')));
  return 'j' + b64u(bytes);
}
export async function decodeList(hash) {
  const h = String(hash || '').replace(/^#/, '');
  if (!h || h.length > 20000) throw new Error('empty');
  const body = h.slice(1);
  let bytes;
  if (h[0] === 'z') bytes = await pipe(unb64u(body), new DecompressionStream('deflate-raw'));
  else if (h[0] === 'j') bytes = unb64u(body);
  else throw new Error('bad prefix');
  return unpackList(JSON.parse(new TextDecoder().decode(bytes)));
}

// ---------- mount compatibility (deliberately simple; shown with a "simplified rules" label) ----------
export const MIRRORLESS = new Set(['Sony E', 'Fujifilm X', 'Nikon Z', 'Canon RF', 'L-Mount', 'Micro Four Thirds', 'Canon EF-M', 'Fujifilm G', 'Hasselblad XCD']);
const NO_RULES = new Set(['Fixed Lens', 'Enlarging', 'Large Format']);
// First-party / well-known adapters that keep autofocus.
const NAMED_ADAPTERS = {
  'Canon EF>Canon RF': "Canon's EF-EOS R adapter keeps autofocus",
  'Canon EF>Canon EF-M': "Canon's EF-EOS M adapter keeps autofocus",
  'Nikon F>Nikon Z': "Nikon's FTZ adapter (autofocus with AF-S/AF-P lenses)",
  'Sony A>Sony E': "Sony's LA-EA adapters",
  'Four Thirds>Micro Four Thirds': "the Olympus/OM MMF adapter keeps autofocus",
  'M42>Pentax K': "a Pentax K–M42 adapter (manual focus)",
};
// Returns {status: 'ok'|'adapter'|'nofit'|'unknown', note}
export function mountCompat(lensMount, bodyMount) {
  if (!lensMount || !bodyMount || NO_RULES.has(lensMount) || NO_RULES.has(bodyMount)) return { status: 'unknown', note: '' };
  if (lensMount === bodyMount) return { status: 'ok', note: 'native mount' };
  const named = NAMED_ADAPTERS[`${lensMount}>${bodyMount}`];
  if (named) return { status: 'adapter', named: true, note: `needs an adapter: ${named}` };
  const lm = MIRRORLESS.has(lensMount), bm = MIRRORLESS.has(bodyMount);
  if (lm && !bm) return { status: 'nofit', note: `won't fit: ${lensMount} is a mirrorless mount and can't go on a ${bodyMount} body` };
  if (lm && bm) return { status: 'nofit', note: `won't fit: ${lensMount} and ${bodyMount} are different mirrorless mounts` };
  if (!lm && bm) return { status: 'adapter', note: `needs an adapter: ${lensMount} lenses adapt to ${bodyMount} (usually manual focus or limited autofocus)` };
  return { status: 'nofit', note: `won't fit: ${lensMount} lenses don't mount on ${bodyMount} bodies` };
}
const RANK = { ok: 3, adapter: 2, nofit: 1, unknown: 0 };
// For each lens in the list, the best result across the bodies in the same list.
export function checkList(items, mountOf = (it) => it.m) {
  const bodies = items.filter((it) => isBodyCat(it.c) && mountOf(it) && !NO_RULES.has(mountOf(it)));
  const out = new Map();
  if (!bodies.length) return out;
  for (const it of items) {
    if (it.c !== 'lens' || !mountOf(it)) continue;
    let best = null;
    for (const b of bodies) {
      const r = mountCompat(mountOf(it), mountOf(b));
      const score = (x) => RANK[x.status] + (x.named ? 0.5 : 0);
      if (!best || score(r) > score(best)) best = { ...r, body: b };
    }
    if (best && best.status !== 'unknown') out.set(it, best);
  }
  return out;
}

// ---------- catalog (built by /kit-data.json) and totals ----------
// Row: [key, name, category, brand, mount, usedMin, usedDealer, usedUrl, bestScore, newPrice, newDealer, newUrl, listingCount]
export function indexCatalog(rows) {
  const byKey = new Map(), byName = new Map();
  for (const r of rows || []) {
    const m = { key: r[0], name: r[1], category: r[2], brand: r[3], mount: r[4], used: r[5], usedDealer: r[6], usedUrl: r[7], score: r[8], newPrice: r[9], newDealer: r[10], newUrl: r[11], count: r[12] };
    byKey.set(m.key, m); byName.set(m.name.toLowerCase(), m);
  }
  return { byKey, byName, rows };
}
export function kitTotals(items, cat) {
  let used = 0, usedN = 0, nw = 0, newN = 0, best = 0, bestN = 0;
  for (const it of items) {
    const m = it.k && cat ? cat.byKey.get(it.k) : null;
    if (!m) continue;
    if (m.used != null) { used += m.used; usedN++; }
    if (m.newPrice != null) { nw += m.newPrice; newN++; }
    const b = [m.used, m.newPrice].filter((x) => x != null);
    if (b.length) { best += Math.min(...b); bestN++; }
  }
  const r2 = (x) => Math.round(x * 100) / 100;
  return { items: items.length, used: r2(used), usedN, new: r2(nw), newN, best: r2(best), bestN };
}
export function groupByCat(items) {
  const g = new Map();
  for (const c of CAT_ORDER) g.set(c, []);
  for (const it of items) g.get(CAT_LABEL[it.c] ? it.c : 'other').push(it);
  return [...g].filter(([, v]) => v.length);
}

// ---------- small DOM helpers ----------
export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const money = (v) => (v == null ? '—' : '$' + Number(v).toLocaleString('en-CA', { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 }));
export const scoreLabel = (s) => (s >= 80 ? 'Great' : s >= 65 ? 'Good' : s >= 45 ? 'Fair' : 'Weak');
export const scoreCls = (s) => (s >= 65 ? 'good' : s >= 45 ? '' : 'warn');

// Heart buttons: <button class="ug-save" data-k data-n data-m data-cat>. Delegated, so client-rendered rows work too.
export function syncSaveButtons(root = document) {
  const s = load();
  const saved = new Set(wishList(s).items.map((i) => i.k).filter(Boolean));
  root.querySelectorAll('.ug-save[data-k]').forEach((b) => {
    const on = saved.has(b.dataset.k);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.title = on ? 'Saved to your wish list (click to remove)' : 'Save to your wish list';
    b.setAttribute('aria-label', b.title);
  });
}
let toastTimer;
function toast(html) {
  let t = document.getElementById('ug-toast');
  if (!t) { t = document.createElement('div'); t.id = 'ug-toast'; t.setAttribute('role', 'status'); document.body.appendChild(t); }
  t.innerHTML = html; t.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
}
export function initSaveButtons(myUrl = '/my/') {
  document.addEventListener('click', (e) => {
    const b = e.target.closest && e.target.closest('.ug-save[data-k]');
    if (!b) return;
    e.preventDefault();
    const s = load(); const w = wishList(s);
    const i = w.items.findIndex((x) => x.k === b.dataset.k);
    if (i >= 0) { w.items.splice(i, 1); toast(`Removed from ${esc(w.name)}.`); }
    else {
      if (w.items.length >= MAX_ITEMS) { toast('Your wish list is full.'); return; }
      w.items.push(cleanItem({ k: b.dataset.k, n: b.dataset.n, m: b.dataset.m, c: defaultCat(b.dataset.cat, b.dataset.m, b.dataset.k) }));
      toast(`Saved to ${esc(w.name)}. <a href="${esc(myUrl)}">View my kit</a>`);
    }
    save(s); syncSaveButtons();
  });
  window.addEventListener('ug:lists', () => syncSaveButtons());
  window.addEventListener('storage', (e) => { if (e.key === STORE_KEY) syncSaveButtons(); });
  window.ugSaveSync = syncSaveButtons;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => syncSaveButtons());
  else syncSaveButtons();
}
