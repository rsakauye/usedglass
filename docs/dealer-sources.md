# Dealer sources

Non-eBay dealers only, as of 2026-11-05. eBay stays on the official Browse API and is not listed here.

Every adapter calls `scraper/http.py` `fetch()`. That sends `User-Agent: UsedGlassBot/0.2 (+https://usedglass.ca/about/#bots)`, waits at least 2 seconds between requests to the same host, and waits longer when robots.txt publishes a higher `Crawl-delay`. It checks robots.txt unless a caller passes `check_robots=False`. Downtown Camera was the only caller that did; it no longer does.

Plot Camera, Camera Traders, and Maple Camera Co. are in `PAUSED_DEALERS` in `scraper/dealers.py`. The daily run (`python -m scraper.run` with no dealer arguments) still lists them so `data/meta.json` records `paused (ToS: scrape ban)` with count 0. The adapter is not called, the skip is not written to `errors`, and yesterday's rows for that dealer are not kept. Names, cities, and sites stay in `DEALERS` so older listings still resolve. Delete that dealer's line from `PAUSED_DEALERS` to fetch it again.

| id | name | site | method | robots checked | rate | ToS (2026-11-05) |
|---|---|---|---|---|---|---|
| thecamerastore | The Camera Store | https://thecamerastore.com | Shopify JSON, collection `pre-owned` | yes | ≥2 s | no clear scrape/spider ban |
| mcbain | McBain Camera | https://www.mcbaincamera.com | HTML POST, `products.php?product_type=Used Equipment` | yes | ≥2 s | no clear scrape/spider ban |
| beauphoto | Beau Photo | https://www.beauphoto.com | WooCommerce Store API, category `1919` | yes | ≥2 s | no clear scrape/spider ban |
| downtowncamera | Downtown Camera | https://downtowncamera.com | Google Sheet CSV export | yes | ≥2 s (host asks 1 s) | UNCHECKED |
| gosselin | Gosselin Photo | https://gosselinphoto.ca | Shopify JSON, collection `equipement-photo-video-usages` | yes | ≥2 s | no clear scrape/spider ban |
| camtec | Camtec Photo | https://www.camtecphoto.com | HTML, `/en/collections/pre-owned?per-page=all` | yes | Crawl-delay 10 | no clear scrape/spider ban |
| plotcamera | Plot Camera | https://www.plotcamera.com | Shopify JSON, collection `all` (adapter kept) | yes, not called while paused | ≥2 s | PAUSED — scrape ban |
| cameratraders | Camera Traders | https://www.camera-traders.com | Shopify JSON, collection `used-equipment` (adapter kept) | yes, not called while paused | ≥2 s | PAUSED — spider/crawl/scrape ban |
| maplecamera | Maple Camera Co. | https://maplecameraco.com | Shopify JSON, collection `all` (adapter kept) | yes, not called while paused | ≥2 s | PAUSED — spider/crawl/scrape ban |
| cameratrading | Camera Trading Company | https://cameratradingcompany.com | Shopify JSON, `/products.json`, used and consignment only | yes | ≥2 s | no explicit scrape/spider ban; copying content needs permission |
| cameracanada | Camera Canada | https://www.cameracanada.com | HTML, ASP.NET catalogue, subcats 267 (used) and 265 (open box) | yes | ≥2 s | no clear scrape/spider ban |

`robots.txt` on 2026-11-05 allows the URL each active adapter requests, including the Downtown Camera sheet export. `docs.google.com` has `Allow: /spreadsheet` (a prefix of `/spreadsheets/...`) and `Crawl-delay: 1`; the fetcher's 2-second floor applies. Camtec publishes `Crawl-delay: 10` for `User-agent: *`, and `fetch()` honours it.

## Terms

Checked by reading the store's own terms page. A missing spider/scrape sentence is recorded as "no clear ban". It is not a grant of permission.

- **plotcamera — PAUSED.** [Terms of service](https://www.plotcamera.com/policies/terms-of-service), User Conduct: "You agree not to misuse our website, submit false information, attempt fraud, interfere with checkout, scrape content, or use our services for unlawful purposes."
- **cameratraders — PAUSED.** [Terms of service](https://www.camera-traders.com/policies/terms-of-service), section 12(i): prohibited to "spam, phish, pharm, pretext, spider, crawl, or scrape". The separate [Terms & Conditions](https://www.camera-traders.com/pages/terms-conditions) page is the warranty and returns policy and does not repeat that clause.
- **maplecamera — PAUSED.** [Terms of service](https://maplecameraco.com/policies/terms-of-service), section 13: "you agree not to … (d) spam, phish, pharm, pretext, spider, crawl, or scrape".
- **thecamerastore.** [Terms of service](https://thecamerastore.com/policies/terms-of-service) covers pricing, online orders, and in-store pickup. No scrape/spider clause.
- **mcbain.** [Online policies](https://www.mcbaincamera.com/terms.php) covers returns, shipping, and price protection. No scrape/spider clause.
- **beauphoto.** [Terms and conditions](https://www.beauphoto.com/terms-and-conditions/) covers shipping, rentals, and consignment. No scrape/spider clause.
- **downtowncamera — UNCHECKED.** [Terms & Conditions](https://downtowncamera.com/terms-conditions) is linked in the footer, but the HTML fetched on 2026-11-05 was navigation and a copyright footer with no terms text, so no clause could be read. [Privacy policy](https://downtowncamera.com/privacy-policy) has no scrape/spider clause. The used list itself is the public sheet linked from [used equipment](https://downtowncamera.com/used-equipment).
- **gosselin.** [Terms of service](https://gosselinphoto.ca/policies/terms-of-service) covers orders, delivery, and returns. No scrape/spider clause. A different host, [impression.gosselinphoto.ca conditions](https://impression.gosselinphoto.ca/conditions-dutilisation), limits reuse of that print shop's content. It is not the equipment catalogue this adapter reads.
- **camtec.** No website-use terms page found. [Privacy policy](https://www.camtecphoto.com/en/privacy-policy) and the [shipping and return policy](https://www.camtecphoto.com/en/our-shipping-pricing-and-return-policy) have no scrape/spider clause.
- **cameratrading.** [Terms of use](https://cameratradingcompany.com/pages/terms-of-use) (same text as `/policies/terms-of-service`): "You may not copy, reproduce, or use website content without permission." No spider, crawl, or scrape sentence. Still fetched; only the three bans above are paused.
- **cameracanada.** Terms are [Legal Information](https://www.cameracanada.com/legal.aspx) (trademarks, disclaimer, user content, Ontario governing law). No scrape/spider clause. There is no `/terms.aspx`.

## API, feed, and agent paths

Nothing below is wired into the scraper. Paused adapters are not called, including any agent endpoint on those stores.

### Shopify (`thecamerastore`, `gosselin`, `plotcamera`, `cameratraders`, `maplecamera`, `cameratrading`)

The adapter reads the public storefront catalogue: `/products.json` or `/collections/{handle}/products.json`. That is not the Shopify Partner API and not the Admin API. Partner API access does not include another merchant's catalogue. Admin `read_products` needs an app the merchant installs and a token they share. No such app or token was found.

Each of these six stores publishes Shopify's shopping-agent surface (HTTP 200 on 2026-11-05):

- `https://{host}/agents.md` — agent instructions
- `https://{host}/.well-known/ucp` — Universal Commerce Protocol profile
- `https://{host}/api/ucp/mcp` — MCP endpoint for that profile

`agents.md` describes product search, carts, and buyer-authorized checkout through UCP/MCP or the browser WebMCP tools, plus the [Shop skill](https://shop.com/SKILL.md) for a shopper's own Shop account (history, Shop Pay, order tracking). It also allows reading public HTML via the sitemap and `/products/{handle}`. It is a per-buyer shopping interface, not a bulk used-price feed, and the daily run does not call it. Platform docs: [Shopify agents](https://shopify.dev/docs/agents). No other product feed was found.

### Beau Photo (WooCommerce)

The adapter uses the public Store API, which does not take keys: `https://www.beauphoto.com/wp-json/wc/store/v1/products`. The authenticated catalogue API is WooCommerce REST (`/wp-json/wc/v3/products`) with a consumer key and secret the store would have to issue. None is published. `https://www.beauphoto.com/agents.md` and `/.well-known/ucp` returned 404. No agent path found.

### Downtown Camera

The store links a public Google Sheet from https://downtowncamera.com/used-equipment (`/spreadsheets/d/1XQx3uaeR_puoGsZn1MZtmdp4uBaZwDjUMf1vzLMlGmo/edit?usp=sharing`). The adapter reads that sheet's CSV export. The Google Sheets API would be the same spreadsheet behind a Google credential; no other feed was found. The site footer says "Powered by dakis". No public Dakis product API was found. `https://downtowncamera.com/agents.md` returned 404.

### McBain, Camtec, Camera Canada

Custom HTML catalogues (PHP, Camtec's own collection page, ASP.NET). No `agents.md`, public REST catalogue, or product feed was found for https://www.mcbaincamera.com, https://www.camtecphoto.com, or https://www.cameracanada.com (`agents.md` returned 404 on each).
