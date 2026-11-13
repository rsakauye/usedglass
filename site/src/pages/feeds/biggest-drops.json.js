import { biggestDrops } from '../../lib/data.js';

// Weekly biggest price drops (data/biggest-drops.json, from scraper/dropsfeed.py), for the Friday social posts.
// model_url is the absolute model page link; model_path stays as the scraper wrote it.
export function GET(context) {
  const site = new URL(import.meta.env.BASE_URL, context.site).href;
  const items = (biggestDrops.items || []).map((i) => ({
    ...i,
    model_url: i.model_key ? new URL(`model/${i.model_key}/`, site).href : null,
  }));
  const body = { ...biggestDrops, count: items.length, items };
  return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}
