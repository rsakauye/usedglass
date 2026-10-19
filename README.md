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
       ├─ rebates.json (Canon / Fujifilm / Nikon Canada promo pages)
       ├─ new-prices.json (Canadian NEW prices, The Camera Store public catalogue: scraper/newprices.py)
       ├─ fx.json (Bank of Canada Valet API: USD, EUR, GBP, JPY in CAD, history + 7/30-day change)
       ├─ currency.json (US landed-cost gaps + "rate moved, prices haven't": scraper/currency.py)
       ├─ Deal Score 0-100 on listings/models/deals (scraper/dealscore.py, formula on /about/deal-score/)
       └─ newsletter.json (data hook for the weekly Kit broadcast: FX headline, currency flags, top-scored deals)
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
| Camera Traders (Victoria) | Shopify `products.json` (`used-equipment`), brand/mount tags used as hints | ~640 items |
| Camera Canada (online, ON) | Server-rendered ASP.NET catalogue: used + open box | ~180 items |
| Maple Camera Co. (Scarborough) | Shopify `products.json`, used only | ~95 items |
| Camera Trading Company (Perth, ON) | Shopify `products.json`, used/consignment only (new film, chemistry and books skipped) | ~55 items |
| Plot Camera (Vancouver) | Shopify `products.json`, used only, grade tags | ~45 items |
| eBay (Canadian sellers) | Official Browse API | needs keys |

Polite by design: robots.txt checked, ≥2 s between requests per host (or the site's crawl-delay), identifiable UA `UsedGlassBot`, one run per day, transient errors retried twice with backoff. If a dealer fails, yesterday's listings are kept and flagged stale.

Not scraped (checked Oct 2026): **Henry's** and **Kerrisdale Cameras** render used inventory client-side
(Henry's Dynamics 365 Commerce, Kerrisdale's Dakis embed), so they would need a headless browser; **Vistek** and
**Leo's Camera Supply** sit behind a Cloudflare bot challenge; **Aden Camera** (Shopify) sells new gear only.

### Scrape-failure alerts
After every run, `python -m scraper.alert` reads `data/meta.json`. If any dealer errored, returned 0 listings, or
fell below 40% of its previous count, it opens (or updates and comments on) a single issue labelled
`scrape-alert`; when every feed is healthy again it comments and closes that issue. Uses the workflow's
`GITHUB_TOKEN` (`issues: write`); without a token it only prints the report.

### Deal rules
A listing is a deal when it is ≥20% (and ≤70%, to filter mismatches) below the median of ≥3 comparable listings (same model key; current listings across dealers + last 90 days), or its price dropped ≥10%, or a new manufacturer rebate page appears. Tunable in `scraper/run.py`.

### Currency watch (/currency/)
- **Rates:** Bank of Canada Valet API (`FXUSDCAD`, `FXEURCAD`, `FXGBPCAD`, `FXJPYCAD`), one request per run, free, no key.
  Attribution shown on the page; rates are indicative.
- **Rate moved, prices haven't:** when USD/CAD moves ≥2.5% over 30 days, Canadian new prices unchanged in that window are
  listed as "may adjust". Needs ≥14 days of our own new-price history (tracking began 2026-10-18).
- **US price gap:** estimated landed CAD = USD × BoC rate + shipping (default $40) + brokerage (default $25) + 5% GST
  (HST provinces pay 13–15%; most cameras/lenses are duty-free). Flagged when ≥5% and ≥$50 under the cheapest
  Canadian price. US offers come from `data/us-offers.json` (hand-checked prices or an affiliate product feed) and,
  automatically, from the eBay Browse API (`EBAY_US` marketplace, new, ships to CA) once `EBAY_CLIENT_ID/SECRET` exist
  (`EBAY_US_GAP=0` turns it off). B&H is not scraped: robots.txt disallows its search/catalogue paths and it sits
  behind a bot challenge; use its affiliate data feed once approved.

### Deal Score
`scraper/dealscore.py`: weighted 0–100 score (history vs comparables 45%, 90-day low 10%, used vs current
Canadian new price adjusted for model age 25%, successor gap 20%, freshness ±8). Curated release dates/successors in
`data/model-meta.json` (cite a manufacturer or reputable review URL for every entry; leave unknowns null).
Models without metadata use history only and say so. Deals are sorted by Deal Score.

## Local development

```bash
python -m unittest tests.test_normalize tests.test_alert tests.test_currency
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

## Newsletter (Kit)
Footer and `/newsletter/` post straight to Kit form `10061701` (`https://app.kit.com/forms/10061701/subscriptions`,
field `email_address`). Override with the repo variable `KIT_FORM_ID` (or `off`). Draft copy for the welcome
email and the first weekly broadcast lives in `newsletter/`.

## Feeds
- `/rss.xml`: deal of the day + flagged deals (for auto-posting to X/Bluesky later)
- `/listings.json`: compact listing array used by the search page
