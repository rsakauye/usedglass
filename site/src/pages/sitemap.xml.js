// Sitemap of every indexable page (static pages + one page per tracked model). No extra dependency.
// <lastmod> is the date the page's content really changed (see lib/lastmod.js), or omitted when unknown,
// so search engines and the IndexNow ping (scripts/indexnow.mjs) only see genuine updates.
import { modelPages } from '../lib/data.js';
import { gitDate, modelLastmod, maxDate } from '../lib/lastmod.js';
import { sitemapEntries } from '../lib/reports.js';
const P = (f) => `site/src/pages/${f}`;
const D = (f) => `data/${f}`;
// path -> source + data files whose changes change what the page shows.
const STATIC = {
  '': [P('index.astro'), D('meta.json')],
  'deals/': [P('deals.astro'), D('deals.json'), D('deal-of-the-day.json')],
  'new/': [P('new.astro'), D('changes.json')],
  'drops/': [P('drops.astro'), D('changes.json')],
  'rebates/': [P('rebates.astro'), D('rebates.json')],
  'currency/': [P('currency.astro'), D('currency.json'), D('fx.json')],
  'dealers/': [P('dealers.astro'), D('meta.json')],
  'models/': null, // = newest model page
  'reports/': null, // = newest report
  'vintage/': [P('vintage.astro'), 'site/src/lib/vintage.js', D('listings.json'), D('find-of-week.json')],
  'events/': [P('events.astro'), D('events.json'), D('clubs.json'), D('galleries-for-rent.json')],
  'adapt/': [P('adapt.astro'), 'site/src/lib/adapt.js', D('mounts.json')],
  'compare/': [P('compare.astro'), D('compare-specs.json'), D('model-traits.json'), D('models.json')],
  'my/': [P('my.astro'), 'site/src/lib/mykit-ui.js', 'site/src/lib/mykit-core.js'],
  'newsletter/': [P('newsletter.astro'), 'site/src/lib/newsletter.js'],
  'about/': [P('about.astro')],
  'about/deal-score/': [P('about/deal-score.astro')],
  'privacy/': [P('privacy.astro')],
  'terms/': [P('terms.astro')],
};
const extra = sitemapEntries();
export function GET() {
  const site = 'https://usedglass.ca/';
  // Live models plus ones last seen within the retain window (modelPages). A key with no state
  // row (reclassified, or only known from an older catalog) uses its recorded last_seen day.
  const modelEntries = modelPages.map((m) => [`model/${m.key}/`, modelLastmod(m.key) || m.last_seen || null]);
  const newestModel = maxDate(modelEntries.map((e) => e[1]));
  const staticEntries = Object.entries(STATIC)
    .filter(([p]) => p !== 'reports/' || extra.length)
    .map(([p, deps]) => [p, p === 'models/' ? newestModel : p === 'reports/' ? maxDate(extra.map((e) => e[1])) : gitDate(deps)]);
  const urls = [...staticEntries, ...extra, ...modelEntries]
    .map(([p, d]) => `  <url><loc>${site}${p}</loc>${d ? `<lastmod>${d}</lastmod>` : ''}</url>`).join('\n');
  return new Response(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
}
