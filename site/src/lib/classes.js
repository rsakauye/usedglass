// Photographer classes (RPG-style), picked on /my/ and stored in this browser only (localStorage).
// Each class lists the /compare/ stats it cares about; that only changes highlighting, never the scores.
export const CLASS_KEY = 'ug.classes.v1';
export const MAX_CLASSES = 3;
// [id, label, 3-letter badge code, stats emphasised on /compare/, one-line flavour]
export const CLASSES = [
  ['street', 'Street', 'STR', ['AGI', 'STB'], 'Small, quiet and always with you'],
  ['sports', 'Sports', 'SPT', ['SPD', 'STA'], 'Fast bursts and a battery that lasts the game'],
  ['wildlife', 'Wildlife', 'WLD', ['SPD', 'RES', 'STA'], 'Reach, speed and long days outside'],
  ['portrait', 'Portrait', 'POR', ['RES', 'STB'], 'Detail for skin, eyes and big prints'],
  ['wedding', 'Wedding', 'WED', ['STA', 'STB', 'VID'], 'Long days, dim churches, a bit of video'],
  ['landscape', 'Landscape', 'LND', ['RES', 'STA'], 'Every pixel, far from a charger'],
  ['astro', 'Astro / Aurora', 'AST', ['RES', 'STA'], 'Cold nights and long exposures'],
  ['vlogger', 'Vlogger', 'VLG', ['VID', 'AGI', 'STB'], 'Handheld video that travels light'],
  ['food', 'Food', 'FOD', ['RES', 'STB'], 'Close detail in restaurant light'],
  ['film', 'Film / Analog', 'FLM', ['AGI', 'RES'], 'Light bodies that pair with old glass'],
  ['news', 'ENG / News', 'ENG', ['VID', 'STA', 'SPD'], 'Get the shot and the clip, all day'],
  ['parent', 'Parent', 'PAR', ['SPD', 'AGI'], 'Fast kids, one free hand'],
  ['macro', 'Macro', 'MAC', ['RES', 'STB'], 'Tiny subjects, steady hands'],
  ['travel', 'Travel', 'TRV', ['AGI', 'STA'], 'Light bag, days between chargers'],
];
export const CLASS_BY_ID = Object.fromEntries(CLASSES.map((c) => [c[0], c]));
export function cleanClasses(v) {
  const out = [];
  for (const id of Array.isArray(v) ? v : []) if (typeof id === 'string' && CLASS_BY_ID[id] && !out.includes(id)) out.push(id);
  return out.slice(0, MAX_CLASSES);
}
export function loadClasses() {
  try { return cleanClasses(JSON.parse(localStorage.getItem(CLASS_KEY) || '[]')); } catch { return []; }
}
export function saveClasses(ids) {
  try { localStorage.setItem(CLASS_KEY, JSON.stringify(cleanClasses(ids))); } catch {}
}
// Stats to emphasise for a set of classes, with the classes that want each one.
export function emphasis(ids) {
  const m = {};
  for (const id of cleanClasses(ids)) for (const st of CLASS_BY_ID[id][3]) (m[st] = m[st] || []).push(CLASS_BY_ID[id][1]);
  return m;
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
export const badgeHtml = (id) => { const c = CLASS_BY_ID[id]; return c ? `<span class="ug-cls" title="${esc(c[4])}"><b>${c[2]}</b>${esc(c[1])}</span>` : ''; };
export const CLASS_CSS = `
.ug-cls { display:inline-flex; align-items:center; gap:.4rem; font:700 .78rem/1 ui-monospace, Menlo, Consolas, monospace; text-transform:uppercase; letter-spacing:.06em; color:#14213d; background:#f7f2e8; border:2px solid #14213d; box-shadow:3px 3px 0 #f4a261; padding:.28rem .5rem .28rem .3rem; border-radius:3px; margin:0 .45rem .45rem 0; }
.ug-cls b { background:#14213d; color:#f4a261; padding:.18rem .3rem; border-radius:2px; }
html[data-theme=dark] .ug-cls { color:#ffd9b0; background:#1f1c18; border-color:#ffad5c; box-shadow:3px 3px 0 #b3261e; }
html[data-theme=dark] .ug-cls b { background:#ffad5c; color:#121110; }
`;
