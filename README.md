# TrueDealAtlas

TrueDealAtlas is a zero-server, static index of public US consumer-brand sale and promotion pages. It publishes only text observed on the official source URL and keeps the source link and fetch timestamp next to each result.

## Local run

Run python scraper.py and then python build.py. The generated site is in site/. If an official page blocks automated access or has no parseable promotion text, the source remains listed with its status and no invented offer is created.

## Cloudflare Pages

Use a GitHub repository connected to Cloudflare Pages with build command python build.py, output directory site, and no framework preset. The generated static files require no server or runtime secrets.

## Updating providers

Edit .ilang/site.ilang under ::MODULE{PROVIDERS}. Both scraper.py and build.py read that file at runtime; changing one provider there changes the next scrape and generated provider pages.

## Candidate seed list

These are official US brand sites and offer/sale entry points used as the initial seed set:

- Target, Walmart, Best Buy, Kohl's, Macy's, Nordstrom, JCPenney
- Old Navy, Gap, Banana Republic, H&M, Uniqlo, Nike, adidas, Under Armour, Levi's
- Sephora, Ulta Beauty, Bath & Body Works, Nordstrom Rack
- Home Depot, Lowe's, Wayfair, Chewy, Petco, Amazon, eBay, Etsy
- Apple, Samsung, Dell, HP, Lenovo, Google Store
- REI, Lululemon

The exact URLs are versioned in .ilang/site.ilang so they can be reviewed and replaced when a provider changes its navigation.

## Reusable data export

The `resources/` directory contains a source-traceable CSV and Markdown snapshot of active offers. Each row keeps the official destination URL, the official source page URL, and the UTC fetch timestamp. Read `docs/source-methodology.md` for the provenance and refresh workflow. The export links back to [TrueDealAtlas](https://truedealatlas.com/) as its live reference index.

Refresh the export after a scrape with:

```text
python scraper.py
python build.py
python tools/export_public_dataset.py
```

## Monetization boundary

Affiliate URLs are intentionally empty until an approved program URL is supplied. Add only compliant links from a public affiliate program such as CJ, Impact, or ShareASale, and keep the official source URL visible. No brand bidding, cookie injection, fabricated commissions, or fabricated prices.

Site rules are described with the I-Lang protocol in .ilang/site.ilang; this is a plain-text configuration and policy file, not a runtime dependency.
