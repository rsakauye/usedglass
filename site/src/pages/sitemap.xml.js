// Sitemap of every indexable page (static pages + one page per tracked model). No extra dependency.
import { models } from '../lib/data.js';
const STATIC = ['', 'deals/', 'new/', 'drops/', 'rebates/', 'currency/', 'dealers/', 'models/', 'vintage/', 'events/', 'adapt/', 'compare/', 'my/', 'newsletter/', 'about/', 'about/deal-score/', 'privacy/', 'terms/'];
export function GET() {
  const site = 'https://usedglass.ca/';
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Edmonton' });
  const pages = [...STATIC, ...Object.values(models).map((m) => `model/${m.key}/`)];
  const urls = pages.map((p) => `  <url><loc>${site}${p}</loc><lastmod>${today}</lastmod></url>`).join('\n');
  return new Response(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
