"""Download local UI assets; not required during the production build."""
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scraper import parse_config
from build import load_data, slug

ROOT = Path(__file__).resolve().parents[1]


def download(url, target):
    if target.exists():
        return True
    try:
        with urlopen(Request(url, headers={"User-Agent": "TrueDealAtlas UI assets"}), timeout=15) as response:
            if target.suffix == ".ico" and not response.headers.get("Content-Type", "").startswith("image/"):
                raise ValueError("Not an image response")
            body = response.read()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        print("Downloaded", target.name)
        return True
    except Exception as error:
        print("Asset unavailable:", target.name, type(error).__name__)
        return False


if __name__ == "__main__":
    download("https://unpkg.com/lucide-static@0.468.0/LICENSE", ROOT / "templates" / "icons" / "LICENSE")
    for name in ("search", "menu", "arrow-up-right", "arrow-right", "heart", "check", "copy", "x", "tag", "external-link", "chevron-down"):
        download("https://unpkg.com/lucide-static@0.468.0/icons/" + name + ".svg", ROOT / "templates" / "icons" / (name + ".svg"))
    _, data = load_data()
    counts = {}
    for offer in data.get("offers", []):
        counts[offer["provider"]] = counts.get(offer["provider"], 0) + 1
    featured = sorted(counts, key=lambda name: (-counts[name], name.lower()))[:8]
    for provider in parse_config()["providers"]:
        if provider["name"] in featured:
            parsed = urlsplit(provider["website"])
            target = ROOT / "templates" / "store-icons" / (slug(provider["name"]) + ".ico")
            download(parsed.scheme + "://" + parsed.netloc + "/favicon.ico", target)
