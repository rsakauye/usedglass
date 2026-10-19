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
