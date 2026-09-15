# ILANG: ROLE=scraper; READ=.ilang/site.ilang; SOURCE=public official pages; NEVER=fake offers/prices
from __future__ import annotations
import html, json, re, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
CONFIG_PATH = ROOT / ".ilang" / "site.ilang"
OUT_PATH = ROOT / "data" / "offers.json"

def parse_config(path: Path = CONFIG_PATH) -> dict:
    providers = []
    text = path.read_text(encoding="utf-8")
    in_providers = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("::MODULE{PROVIDERS"):
            in_providers = True
            continue
        if in_providers and line.startswith("::"):
            in_providers = False
        if in_providers and "|" in line:
            parts = [part.strip() for part in line.split("|")]
            if len(parts) >= 3 and all(parts[:3]):
                providers.append({"name": parts[0], "website": parts[1], "offer_url": parts[2], "affiliate": parts[3] if len(parts) > 3 else ""})
    state = re.search(r"::STATE\{@SITE,([^}]+)\}", text)
    meta = {}
    if state:
        for part in state.group(1).split(","):
            if ":" in part:
                key, value = part.split(":", 1)
                meta[key.strip()] = value.strip()
    return {"meta": meta, "providers": providers}

class PageTextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.links = []; self.href = None; self.link_text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href"); self.link_text = []
    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            label = " ".join(self.link_text).strip()
            if label: self.links.append((label, self.href))
            self.href = None
    def handle_data(self, data):
        clean = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if clean:
            self.parts.append(clean)
            if self.href is not None: self.link_text.append(clean)

OFFER_WORDS = re.compile(r"\b(sale|deal|coupon|promo|offer|save|off|clearance|markdown|discount|free shipping|cash back|rewards)\b", re.I)
PERCENT = re.compile(r"\b(?:up to\s*)?(\d{1,3})\s*%\s*(?:off)?\b", re.I)
MONEY = re.compile(r"(?:\$\s?\d[\d,]*(?:\.\d{2})?)")
DATE = re.compile(r"(?:through|until|ends?|expires?)\s+([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)", re.I)

def fetch(url):
    request = Request(url, headers={"User-Agent": "TrueDealAtlasBot/1.0 (+public-offer-index)"})
    with urlopen(request, timeout=20) as response:
        raw = response.read(2_000_000)
        return raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")

def normalize_title(text, provider):
    text = re.sub(r"\s+", " ", text).strip(" -|:")
    if len(text) > 180: text = text[:177].rstrip() + "..."
    return text if text.lower().startswith(provider.lower()) else f"{provider}: {text}"

def extract_offers(provider, page):
    parser = PageTextParser(); parser.feed(page)
    candidates = [(part, provider["offer_url"]) for part in parser.parts if OFFER_WORDS.search(part) and len(part) >= 12]
    candidates += [(label, urljoin(provider["offer_url"], href)) for label, href in parser.links if OFFER_WORDS.search(label) and len(label) >= 8]
    seen, offers = set(), []
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for text, offer_url in candidates:
        key = re.sub(r"\W+", " ", text.lower()).strip()
        if key in seen: continue
        seen.add(key)
        offer = {"provider": provider["name"], "title": normalize_title(text, provider["name"]), "offer_url": offer_url, "source_url": provider["offer_url"], "fetched_at": fetched_at, "active": True}
        percent, money, date_match = PERCENT.search(text), MONEY.search(text), DATE.search(text)
        if percent: offer["discount_percent"] = int(percent.group(1))
        if money: offer["price"], offer["currency"] = money.group(0).replace("$", "").replace(",", "").strip(), "USD"
        if date_match: offer["valid_until_text"] = date_match.group(1)
        offers.append(offer)
        if len(offers) >= 8: break
    return offers

def main():
    config = parse_config(); all_offers = []; provider_status = []
    for provider in config["providers"]:
        try:
            offers = extract_offers(provider, fetch(provider["offer_url"]))
            all_offers.extend(offers)
            provider_status.append({"name": provider["name"], "source_url": provider["offer_url"], "status": "ok", "offer_count": len(offers)})
        except Exception as exc:
            provider_status.append({"name": provider["name"], "source_url": provider["offer_url"], "status": "error", "error": str(exc)[:180], "offer_count": 0})
        time.sleep(0.15)
    payload = {"generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "brand": config["meta"].get("brand", "TrueDealAtlas"), "niche": config["meta"].get("niche", "US consumer brand coupons and discounts"), "locale": config["meta"].get("locale", "en-US"), "providers": provider_status, "offers": all_offers}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_offers)} offers from {len(provider_status)} providers")

if __name__ == "__main__": main()
