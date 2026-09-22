"""Export the source-traceable offer snapshot into reusable text formats."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "offers.json"
OUT = ROOT / "resources"


def clean(value: object) -> str:
    text = str(value or "")
    # The scraper uses a private marker for percent signs in a few sources.
    text = text.replace("\ue017", "%").replace("\ufffd", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    offers = [offer for offer in payload.get("offers", []) if offer.get("active", True)]
    offers.sort(key=lambda row: (clean(row.get("provider")), clean(row.get("title"))))
    OUT.mkdir(exist_ok=True)

    fields = [
        "provider",
        "title",
        "offer_text",
        "conditions",
        "discount_percent",
        "offer_url",
        "source_url",
        "fetched_at",
    ]
    with (OUT / "official-offers.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for offer in offers:
            writer.writerow({field: clean(offer.get(field)) for field in fields})

    generated_at = clean(payload.get("generated_at"))
    provider_count = len(payload.get("providers", []))
    lines = [
        "# Official US Consumer Offers",
        "",
        "This snapshot is exported from [TrueDealAtlas](https://truedealatlas.com/), an independent index of public offer pages from official US consumer brands.",
        "",
        f"- Snapshot time: `{generated_at}` (UTC)",
        f"- Active offers in this snapshot: **{len(offers)}**",
        f"- Configured official sources: **{provider_count}**",
        "- Source policy: every row keeps both the official detail URL and the source page URL.",
        "",
        "## Fields",
        "",
        "| Field | Meaning |",
        "| --- | --- |",
        "| `provider` | Brand or retailer name |",
        "| `title` | Title observed in the source page |",
        "| `offer_text` | Offer text observed in the source page |",
        "| `conditions` | Eligibility or scope text when exposed |",
        "| `discount_percent` | Parsed percentage when the source states one; blank otherwise |",
        "| `offer_url` | Official detail or destination URL |",
        "| `source_url` | Official page checked by the scraper |",
        "| `fetched_at` | UTC fetch timestamp |",
        "",
        "## Data use",
        "",
        "The CSV is a point-in-time research snapshot, not a guarantee that an offer remains active. Verify terms at the official source before relying on a row. The project does not invent prices, expiration dates, or commission claims.",
        "",
        "## Refresh",
        "",
        "Run `python scraper.py`, then `python build.py`, then `python tools/export_public_dataset.py` to refresh the snapshot.",
        "",
        "## License",
        "",
        "The export is available under [CC BY 4.0](../LICENSE-CC-BY-4.0.txt). The exporter script is available under the repository's MIT license.",
        "",
    ]
    (OUT / "official-offers.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
