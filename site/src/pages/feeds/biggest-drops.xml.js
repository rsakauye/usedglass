import { biggestDrops } from '../../lib/data.js';

const esc = (s) => String(s ?? '').replace(/[<>&'"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c]));
const cad = (v) => '$' + Number(v).toLocaleString('en-CA', { maximumFractionDigits: 2 });
const rfc822 = (day) => (day ? new Date(day + 'T12:00:00Z').toUTCString() : null);

// Weekly biggest price drops as RSS 2.0. Same data as /feeds/biggest-drops.json.
export function GET(context) {
  const site = new URL(import.meta.env.BASE_URL, context.site).href;
  const { week_start: start, week_end: end } = biggestDrops;
  const body = (biggestDrops.items || []).map((i) => {
    const off = Math.round(i.pct * 100);
    const model = i.model_key ? ` Model page: ${new URL(`model/${i.model_key}/`, site).href}` : '';
    const date = rfc822(i.drop_date || end);
    return `
    <item>
      <title>${esc(`${i.title}: ${cad(i.old_price)} to ${cad(i.new_price)} (-${off}%) at ${i.dealer}`)}</title>
      <link>${esc(i.url)}</link>
      <guid isPermaLink="false">${esc(`drop-${i.id}-${end}-${i.new_price}`)}</guid>${date ? `
      <pubDate>${date}</pubDate>` : ''}
      <description>${esc(`Was ${cad(i.old_price)}, now ${cad(i.new_price)} at ${i.dealer}. Down ${cad(i.saved_cad)} (${off}%) on ${i.drop_date}.${model}`)}</description>
    </item>`;
  }).join('');
  const range = start && end ? ` Week of ${start} to ${end}.` : '';
  const built = rfc822(end);
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>UsedGlass.ca: biggest used-gear price drops this week</title>
  <link>${esc(new URL('drops/', site).href)}</link>
  <description>The largest price drops on used cameras and lenses at Canadian dealers over the last seven days.${esc(range)}</description>
  <language>en-ca</language>${built ? `
  <lastBuildDate>${built}</lastBuildDate>` : ''}${body}
</channel></rss>`;
  return new Response(xml, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
}
