// Monthly used-price reports, computed at build time from our own daily snapshots (data/history/*.json),
// listing state (data/state.json: listing -> model) and today's listings. Nothing is estimated or invented:
// every number is a price a Canadian dealer showed on a day our daily scrape ran.
// The current month refreshes with each daily build; past months keep their numbers while the history exists.
import fs from 'node:fs';
import path from 'node:path';
import { models, listings, meta } from './data.js';

const DATA_DIR = process.env.DATA_DIR || path.resolve(process.cwd(), '..', 'data');
const HIST = path.join(DATA_DIR, 'history');
const readJson = (f, fb) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return fb; } };

// Which reports to publish each month. Add a line to add a report.
export const REPORT_TOPICS = [
  { brand: 'Fujifilm', category: 'camera', slug: 'used-fujifilm-camera-prices', title: 'Used Fujifilm camera prices in Canada', noun: 'Fujifilm camera bodies' },
];
// Obvious accessories that the model matcher can mistake for a body (e.g. "BLC-XT10" is a leather case).
// Kept narrow on purpose: bodies are often sold 'with battery' or 'with grip'. The outlier rule below catches the rest.
const ACCESSORY = /(\bblc-|\bhalf[- ]case\b|\bleather case\b|\bcamera case\b|\bscreen protector\b|\bl-?bracket\b)/i;
const median = (a) => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const round = (v) => (v == null ? null : Math.round(v * 100) / 100);
const monthLabel = (ym) => new Date(ym + '-15T12:00:00Z').toLocaleDateString('en-CA', { month: 'long', year: 'numeric', timeZone: 'UTC' });
const dayLabel = (d) => new Date(d + 'T12:00:00Z').toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' });

let cache = null;
function load() {
  if (cache) return cache;
  let files = [];
  try { files = fs.readdirSync(HIST).filter((f) => /^\d{4}-\d{2}-\d{2}\.json$/.test(f)).sort(); } catch {}
  const days = files.map((f) => ({ date: f.slice(0, 10), prices: (readJson(path.join(HIST, f), {}).prices) || {} }));
  const state = readJson(path.join(DATA_DIR, 'state.json'), {});
  const byId = Object.fromEntries(listings.map((l) => [l.id, l]));
  cache = { days, state, byId };
  return cache;
}

function build(ym, topic) {
  const { days, state, byId } = load();
  const inMonth = days.filter((d) => d.date.startsWith(ym));
  if (!inMonth.length) return null;
  const prefix = `${topic.category}-${topic.brand.toLowerCase()}-`;
  const seen = new Map(); // listing id -> {key, prices: [[date, price]]}
  for (const d of inMonth) {
    for (const [id, price] of Object.entries(d.prices)) {
      const key = state[id]?.mk || byId[id]?.model_key;
      if (!key || !key.startsWith(prefix) || !(price > 0)) continue;
      const title = byId[id]?.title || '';
      if (title && ACCESSORY.test(title)) continue;
      // Camera reports: skip lenses the matcher filed under a body name (e.g. "XF 18mm f/1.4"), unless it's a kit ("with" / "w/" / "kit").
      if (topic.category === 'camera' && title && /\bXF\s?\d|\d{2,3}\s?mm\b/i.test(title) && !/\b(with|w\/|kit|body)\b/i.test(title)) continue;
      // Under $150 is never a used body from these brands at a dealer; it's an accessory or a typo.
      if (topic.category === 'camera' && price < 150) continue;
      if (!seen.has(id)) seen.set(id, { id, key, prices: [] });
      seen.get(id).prices.push([d.date, price]);
    }
  }
  // Group by model, then drop price outliers (< 30% of the model's median), which are almost always accessories.
  const byModel = new Map();
  for (const l of seen.values()) { if (!byModel.has(l.key)) byModel.set(l.key, []); byModel.get(l.key).push(l); }
  const lastDay = inMonth.at(-1).date;
  const rows = [];
  const drops = [];
  const dealersUsed = new Set();
  let excluded = 0;
  for (const [key, ls] of byModel) {
    const med0 = median(ls.map((l) => l.prices.at(-1)[1]));
    const keep = ls.length >= 2 ? ls.filter((l) => l.prices.at(-1)[1] >= 0.3 * med0) : ls;
    excluded += ls.length - keep.length;
    if (!keep.length) continue;
    const last = keep.map((l) => l.prices.at(-1)[1]);
    const all = keep.flatMap((l) => l.prices.map((p) => p[1]));
    const m = models[key];
    const name = m?.name || byId[keep[0].id]?.model_name || key.slice(prefix.length).replace(/-/g, ' ');
    for (const l of keep) {
      const dealer = byId[l.id]?.dealer || meta.dealer_info?.[l.id.split('-')[0]]?.name || l.id.split('-')[0];
      dealersUsed.add(dealer);
      const first = l.prices[0][1], now = l.prices.at(-1)[1];
      if (now < first) drops.push({ key, name, hasPage: !!m, dealer, from: first, to: now, pct: (now - first) / first, onSale: l.prices.at(-1)[0] === lastDay, url: byId[l.id]?.url || null });
    }
    rows.push({ key, name, hasPage: !!m, listings: keep.length, onSaleNow: keep.filter((l) => l.prices.at(-1)[0] === lastDay).length,
      median: round(median(last)), low: round(Math.min(...all)), high: round(Math.max(...all)) });
  }
  rows.sort((a, b) => b.listings - a.listings || (b.median || 0) - (a.median || 0) || a.name.localeCompare(b.name));
  drops.sort((a, b) => a.pct - b.pct);
  return {
    slug: `${ym}-${topic.slug}`, ym, month: monthLabel(ym), topic,
    title: `${topic.title}, ${monthLabel(ym)}`,
    from: inMonth[0].date, to: lastDay, fromLabel: dayLabel(inMonth[0].date), toLabel: dayLabel(lastDay), daysCount: inMonth.length,
    complete: ym < (meta.date || lastDay).slice(0, 7),
    totals: { listings: [...seen.values()].length - excluded, models: rows.length, dealers: dealersUsed.size, onSaleNow: rows.reduce((s, r) => s + r.onSaleNow, 0), excluded },
    dealers: [...dealersUsed].sort(), rows, drops: drops.slice(0, 10),
  };
}

let all = null;
export function getReports() {
  if (all) return all;
  const { days } = load();
  const months = [...new Set(days.map((d) => d.date.slice(0, 7)))].sort().reverse();
  all = months.flatMap((ym) => REPORT_TOPICS.map((t) => build(ym, t))).filter((r) => r && r.rows.length);
  return all;
}
// [path, lastmod] pairs for the sitemap: a report changes only when a new day of data lands in its month.
export function sitemapEntries() {
  const rs = getReports();
  return rs.map((r) => [`reports/${r.slug}/`, r.to]);
}
