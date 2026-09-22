# Official US Consumer Offers

This snapshot is exported from [TrueDealAtlas](https://truedealatlas.com/), an independent index of public offer pages from official US consumer brands.

- Snapshot time: `2026-09-17T07:02:45+00:00` (UTC)
- Active offers in this snapshot: **110**
- Configured official sources: **71**
- Source policy: every row keeps both the official detail URL and the source page URL.

## Fields

| Field | Meaning |
| --- | --- |
| `provider` | Brand or retailer name |
| `title` | Title observed in the source page |
| `offer_text` | Offer text observed in the source page |
| `conditions` | Eligibility or scope text when exposed |
| `discount_percent` | Parsed percentage when the source states one; blank otherwise |
| `offer_url` | Official detail or destination URL |
| `source_url` | Official page checked by the scraper |
| `fetched_at` | UTC fetch timestamp |

## Data use

The CSV is a point-in-time research snapshot, not a guarantee that an offer remains active. Verify terms at the official source before relying on a row. The project does not invent prices, expiration dates, or commission claims.

## Refresh

Run `python scraper.py`, then `python build.py`, then `python tools/export_public_dataset.py` to refresh the snapshot.

## License

The export is available under [CC BY 4.0](../LICENSE-CC-BY-4.0.txt). The exporter script is available under the repository's MIT license.
