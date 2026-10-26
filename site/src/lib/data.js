import fs from 'node:fs';
import path from 'node:path';

const DATA_DIR = process.env.DATA_DIR || path.resolve(process.cwd(), '..', 'data');

function read(name, fallback) {
  try {
    return JSON.parse(fs.readFileSync(path.join(DATA_DIR, name), 'utf8'));
  } catch {
    return fallback;
  }
}

export const listings = read('listings.json', []);
export const models = read('models.json', {});
export const meta = read('meta.json', { dealers: {}, dealer_info: {} });
// Models with no listing today, last matched within retain_days. Identity and the last price/date
// come from data/model-seen.json (written by the scraper from real listings). Not merged into `models`,
// so counts, the A–Z index and the kit catalog stay "for sale today".
const seenRoot = read('model-seen.json', {});
const seenModels = seenRoot && typeof seenRoot.models === 'object' && seenRoot.models ? seenRoot.models : {};
const retainDays = Number(seenRoot.retain_days) > 0 ? Number(seenRoot.retain_days) : 90;
const KEY_OK = /^[a-z0-9][a-z0-9_-]*$/;
function isoShift(iso, days) {
  const t = Date.parse(`${iso}T00:00:00Z`);
  if (Number.isNaN(t)) return null;
  return new Date(t + days * 86400000).toISOString().slice(0, 10);
}
const seenCutoff = meta.date ? isoShift(meta.date, -retainDays) : null;
function dormantFromSeen(key, e) {
  if (!KEY_OK.test(key) || models[key] || !e || typeof e.name !== 'string' || !e.name.trim()) return null;
  if (typeof e.last_seen !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(e.last_seen)) return null;
  if (seenCutoff && e.last_seen < seenCutoff) return null;
  const lastPrice = typeof e.last_price === 'number' && e.last_price > 0 ? e.last_price : null;
  const row = {
    key, name: e.name.trim(), category: e.category || null, brand: e.brand || null, mount: e.mount || null,
    listing_ids: [], dealers: [], count: 0, min_price: null, median_price: null,
    median_90d: typeof e.median_90d === 'number' && e.median_90d > 0 ? e.median_90d : null,
    observations_90d: Number.isInteger(e.observations_90d) && e.observations_90d > 0 ? e.observations_90d : 0,
    median_90d_as_of: e.median_90d_as_of || e.last_seen, last_seen: e.last_seen, last_price: lastPrice, dormant: true,
  };
  if (typeof e.new_price === 'number' && e.new_price > 0 && typeof e.new_price_url === 'string') {
    row.new_price = e.new_price;
    row.new_price_url = e.new_price_url;
    row.new_price_dealer = e.new_price_dealer || '';
  }
  return row;
}
export const dormantModels = Object.entries(seenModels).map(([k, e]) => dormantFromSeen(k, e)).filter(Boolean);
export const modelPages = [...Object.values(models), ...dormantModels];
export const modelByKey = Object.fromEntries(modelPages.map((m) => [m.key, m]));
export const changes = read('changes.json', { new_today: [], price_dropped: [] });
export const deals = read('deals.json', { deals: [], deal_of_the_day: null });
export const dotdHistory = read('deal-of-the-day.json', []);
export const rebates = read('rebates.json', { items: [], manual_check: [] });
export const fx = read('fx.json', { series: {}, latest: {} });
export const currency = read('currency.json', { gaps: [], rate_moved: { items: [] }, fx_latest: {} });
export const modelMeta = read('model-meta.json', { models: {} }).models || {};
export const byId = Object.fromEntries(listings.map((l) => [l.id, l]));

export const BASE = import.meta.env.BASE_URL.endsWith('/') ? import.meta.env.BASE_URL : import.meta.env.BASE_URL + '/';
export const u = (p = '') => BASE + String(p).replace(/^\//, '');

export const money = (v) =>
  v == null ? '—' : '$' + Number(v).toLocaleString('en-CA', { minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2 });

export function asOf(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('en-CA', {
    timeZone: 'America/Edmonton', year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }) + ' MT';
}

export const shortDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-CA', { timeZone: 'America/Edmonton', month: 'short', day: 'numeric' }) : '');

export const modelUrl = (key) => u(`model/${key}/`);
export const uniqSorted = (arr) => [...new Set(arr.filter(Boolean))].sort((a, b) => a.localeCompare(b));

export const pct = (v, digits = 1) => (v == null ? '—' : (v > 0 ? '+' : '') + (v * 100).toFixed(digits) + '%');
export const scoreLabel = (s) => (s >= 80 ? 'Great' : s >= 65 ? 'Good' : s >= 45 ? 'Fair' : 'Weak');
export const scoreClass = (s) => (s >= 65 ? 'good' : s >= 45 ? '' : 'warn');
