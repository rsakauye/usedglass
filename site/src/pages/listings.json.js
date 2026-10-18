import { listings } from '../lib/data.js';

// Compact payload for client-side search/filter on the home page.
export function GET() {
  const rows = listings.map((l) => [
    l.title, l.dealer, l.brand || '', l.mount || '', l.condition || '', l.category, l.price_cad, l.url,
    l.model_key || '', l.fetched_at, l.first_seen || '', l.prev_price || 0, l.location || '',
  ]);
  return new Response(JSON.stringify(rows), { headers: { 'Content-Type': 'application/json' } });
}
