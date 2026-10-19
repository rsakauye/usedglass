import { models, byId } from '../lib/data.js';

// Compact model catalog for /my/ and /kit/ (client-side kit builder).
// Row: [key, name, category, brand, mount, usedMin, usedDealer, usedUrl, bestScore, newPrice, newDealer, newUrl, listingCount]
export function GET() {
  const rows = Object.values(models).map((m) => {
    const cheapest = (m.listing_ids || []).map((id) => byId[id]).filter((l) => l && l.price_cad != null)
      .sort((a, b) => a.price_cad - b.price_cad)[0];
    return [
      m.key, m.name, m.category, m.brand || '', m.mount || '',
      cheapest ? cheapest.price_cad : m.min_price ?? null, cheapest ? cheapest.dealer : '', cheapest ? cheapest.url : '',
      m.best_score ?? null, m.new_price ?? null, m.new_price_dealer || '', m.new_price_url || '', m.count || 0,
    ];
  }).sort((a, b) => a[1].localeCompare(b[1]));
  return new Response(JSON.stringify(rows), { headers: { 'Content-Type': 'application/json' } });
}
