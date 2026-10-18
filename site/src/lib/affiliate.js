// Affiliate link helpers. Amazon.ca Associates tracking ID comes from the non-secret
// repo variable AMAZON_TAG (passed to the build as PUBLIC_AMAZON_TAG); defaults to usedglass-20.
export const AMAZON_TAG = (import.meta.env.PUBLIC_AMAZON_TAG || 'usedglass-20').trim();

// rel value for every paid/affiliate link (Google + FTC/Competition Bureau friendly).
export const SPONSORED_REL = 'sponsored nofollow noopener';

export const AMAZON_DISCLOSURE = 'As an Amazon Associate I earn from qualifying purchases.';

const isAmazonCa = (host) => /(^|\.)amazon\.ca$/i.test(host);

// Ensure any amazon.ca URL carries our tag (replaces an existing tag). Other URLs pass through untouched.
export function withAmazonTag(url) {
  try {
    const x = new URL(url);
    if (!isAmazonCa(x.hostname) || !AMAZON_TAG) return url;
    x.searchParams.set('tag', AMAZON_TAG);
    return x.toString();
  } catch {
    return url;
  }
}

// Amazon.ca search URL for a gear model, e.g. "Sony FE 85mm f/1.8 (Sony E)" -> ?k=Sony+FE+85mm+f%2F1.8+Sony+E
export function amazonSearchUrl(query) {
  const q = String(query || '').replace(/[()]/g, ' ').replace(/\s+/g, ' ').trim();
  return withAmazonTag(`https://www.amazon.ca/s?k=${encodeURIComponent(q)}`);
}
