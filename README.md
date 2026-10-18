# UsedGlass.ca

Used camera & lens prices from Canadian dealers in one search, refreshed daily. Static site + daily data pipeline, built to run on its own.

- **Preview (GitHub Pages):** https://rsakauye.github.io/usedglass/
- **Production (planned):** https://usedglass.ca on Cloudflare Pages

## How it works

```
GitHub Actions (daily 12:00 UTC ≈ 6 a.m. Mountain)
  └─ python -m scraper.run
       ├─ dealer adapters (scraper/dealers.py)  → normalized listings
       ├─ eBay Browse API (scraper/ebay.py)      → skipped unless keys are set
       ├─ normalize.py: brand, mount, category, condition grade, model key (heuristic, no AI)
       ├─ history/state: data/history/YYYY-MM-DD.json, data/state.json (first seen, price changes)
       ├─ models.json (grouped models, medians), changes.json (new today, price drops)
       ├─ deals.json + deal-of-the-day.json (steep discounts vs comparable median, drops, new rebates)
       └─ rebates.json (Canon / Fujifilm / Nikon Canada promo pages)
  └─ commit data/ → build Astro site (site/) → publish preview to gh-pages
```

### Dealers

| Dealer | Method | Notes |
|---|---|---|
| McBain Camera (Edmonton) | HTML search POST | ~990 items |
| Downtown Camera (Toronto) | Public Google Sheet CSV linked from their site | ~850 items |
| Gosselin (Québec) | Shopify `products.json` | ~450 items |
| Beau Photo (Vancouver) | WooCommerce Store API | ~390 items |
| Camtec (Montréal) | HTML, honours `Crawl-delay: 10` | ~130 items |
| The Camera Store (Calgary) | Shopify `products.json` | ~90 items |
| eBay (Canadian sellers) | Official Browse API | needs keys |

Polite by design: robots.txt checked, ≥2 s between requests per host (or the site's crawl-delay), identifiable UA `UsedGlassBot`, one run per day. If a dealer fails, yesterday's listings are kept and flagged stale.

### Deal rules
A listing is a deal when it is ≥20% (and ≤70%, to filter mismatches) below the median of ≥3 comparable listings (same model key; current listings across dealers + last 90 days), or its price dropped ≥10%, or a new manufacturer rebate page appears. Tunable in `scraper/run.py`.

## Local development

```bash
python -m unittest tests.test_normalize
python -m scraper.run                 # all dealers; or: python -m scraper.run mcbain camtec
cd site && npm ci && npm run dev      # reads ../data
```

## Deploy to Cloudflare Pages (production)
The daily workflow deploys `site/dist` to the Cloudflare Pages project `usedglass` with
`wrangler pages deploy` (direct upload), right after the GitHub Pages preview. The step is skipped
until both `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` secrets exist; the first run with
secrets creates the project. Production builds use `BASE_PATH=/` and `SITE_URL` from the repo
variable `SITE_URL` (default `https://usedglass.ca`).

Cloudflare zone `usedglass.ca` (free plan) has proxied CNAMEs `usedglass.ca` and `www` → `usedglass.pages.dev`
and a 301 redirect rule `www` → apex. Attach `usedglass.ca` and `www.usedglass.ca` as custom domains
on the Pages project (Workers & Pages → usedglass → Custom domains).

## Secrets (repo → Settings → Secrets and variables → Actions)
| Secret | Where from | Required |
|---|---|---|
| `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET` | eBay Developers Program → production keyset | for eBay listings |
| `EBAY_CAMPAIGN_ID` | eBay Partner Network campaign | optional, adds affiliate tracking |
| `CLOUDFLARE_API_TOKEN` | Cloudflare → My Profile → API Tokens → custom token, *Account → Cloudflare Pages → Edit* | for usedglass.ca deploys |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account id | for usedglass.ca deploys |

## Feeds
- `/rss.xml`: deal of the day + flagged deals (for auto-posting to X/Bluesky later)
- `/listings.json`: compact listing array used by the search page
