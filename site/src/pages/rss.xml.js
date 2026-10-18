import { deals, dotdHistory } from '../lib/data.js';

const esc = (s) => String(s ?? '').replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]));

export function GET(context) {
  const site = new URL(import.meta.env.BASE_URL, context.site).href;
  const items = [];
  for (const d of [...dotdHistory].reverse().slice(0, 30)) {
    items.push({ ...d, title: `Deal of the day: ${d.title}${d.price_cad ? ` · $${d.price_cad}` : ''} (${d.dealer})`, guid: `dotd-${d.date}`, date: d.date });
  }
  for (const d of (deals.deals || []).slice(0, 20)) {
    items.push({ ...d, title: `${d.title}${d.price_cad ? ` · $${d.price_cad}` : ''} (${d.dealer})`, guid: `deal-${d.id}-${d.price_cad}`, date: deals.date });
  }
  const body = items.map((i) => `
    <item>
      <title>${esc(i.title)}</title>
      <link>${esc(i.url)}</link>
      <guid isPermaLink="false">${esc(i.guid)}</guid>
      <pubDate>${new Date((i.date || deals.date) + 'T12:00:00Z').toUTCString()}</pubDate>
      <description>${esc((i.reasons || []).join('; '))}</description>
    </item>`).join('');
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>UsedGlass.ca: used camera deals in Canada</title>
  <link>${esc(site)}</link>
  <description>Daily deal of the day and steep discounts on used cameras and lenses from Canadian dealers.</description>
  <language>en-ca</language>${body}
</channel></rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
}
