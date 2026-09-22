# TrueDealAtlas Source Methodology

TrueDealAtlas indexes public sale and promotion pages published by US consumer brands and retailers. The configured source list is stored in `.ilang/site.ilang` so the provider set, source URL, and fetch mode can be reviewed in one place.

## Provenance

Each offer row is retained only when the scraper can connect it to a public official source. The generated pages show the source URL and the UTC fetch timestamp next to the observed offer text. If a source is blocked or does not expose reliable promotion text, the pipeline records the source status instead of inventing an offer.

## Refresh pipeline

1. `python scraper.py` fetches the configured public sources.
2. `python build.py` writes the static pages, provider pages, sitemap, and robots file.
3. `python tools/export_public_dataset.py` writes the reusable CSV and Markdown snapshot in `resources/`.

The GitHub Actions workflow runs the first two steps every six hours. The export command can be run locally after a refresh when a new research snapshot is needed.

## Interpretation

The dataset is a point-in-time index, not a warranty of availability. A percentage is included only when a source page exposes one that the parser can recognize. Blank values are intentional. Users should verify eligibility, inventory, dates, and terms at the official destination before purchase.

For the current public index, see [TrueDealAtlas](https://truedealatlas.com/). The link is provided for provenance and reproducibility, not as a claim that every offer remains active.
