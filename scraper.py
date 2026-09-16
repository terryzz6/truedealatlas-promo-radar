# ILANG: ROLE=scraper; READ=.ilang/site.ilang; SOURCE=public official pages; NEVER=fake offers/prices
from __future__ import annotations
import base64, html, json, os, re, shutil, socket, struct, subprocess, tempfile, time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
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
                providers.append({"name": parts[0], "website": parts[1], "offer_url": parts[2], "affiliate": parts[3] if len(parts) > 3 else "", "fetch_mode": parts[4] if len(parts) > 4 else "static"})
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
        super().__init__(); self.parts = []; self.links = []; self.href = None; self.link_text = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "template"):
            self.skip += 1
            return
        if tag == "a":
            self.href = dict(attrs).get("href"); self.link_text = []
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template") and self.skip:
            self.skip -= 1
            return
        if tag == "a" and self.href:
            label = " ".join(self.link_text).strip()
            if label: self.links.append((label, self.href))
            self.href = None
    def handle_data(self, data):
        if self.skip:
            return
        clean = re.sub(r"\s+", " ", html.unescape(data)).strip()
        if clean:
            self.parts.append(clean)
            if self.href is not None: self.link_text.append(clean)

PERCENT = re.compile(r"\b(?:(up to|extra|additional)\s+)?(\d{1,3})\s*%\s*off\b", re.I)
MONEY_OFF = re.compile(r"\b(?:save\s+(?:up to\s+)?|(?:get|take)\s+)?(\$\s?\d[\d,]*(?:\.\d{2})?)\s*off\b", re.I)
FREE_SHIPPING = re.compile(r"\bfree\s+(?:standard\s+)?shipping\b", re.I)
PROMO_CODE = re.compile(r"(?i:\b(?:(?:use|apply|with|promo)\s+(?:promo\s+)?code|code)\s*:?\s*)([A-Z0-9][A-Z0-9_-]{2,})\b")
BOGO_OR_GIFT = re.compile(r"\b(?:buy\s+(?:one|1)\s+get\s+(?:one|1)|free\s+gift|gift\s+with\s+purchase)\b", re.I)
LIMITED_EVENT = re.compile(r"\b(?:limited[- ]time\s+(?:sale|deal|event)|deal days?|flash sale|sale ends?|ends?\s+(?:today|tonight|on\b)|through\s+[A-Z][a-z]+\s+\d{1,2})\b", re.I)
CLEARANCE_PRICE = re.compile(r"\bclearance\s+(?:under|from)\s+(\$\s?\d[\d,]*(?:\.\d{2})?)\b", re.I)
EXCLUDED_TEXT = re.compile(r"\b(?:terms? of (?:sale|use|service)|privacy|frequently asked questions?|faq|rewards?(?: loyalty)?(?: program)?|customer service|store locator|find a store|return policy|shipping policy|accessibility)\b", re.I)
EXCLUDED_PATH = re.compile(r"(?:^|[-_/])(?:privacy|faq|help|customer-service|store-locator|return-policy|terms-of-sale)(?:[-_/.]|$)", re.I)
FRAGMENT_START = re.compile(r"^(?:and|or|but|because|by|while|additionally|which|that|then|without this product|connectivity discounts are)\b", re.I)
FRAGMENT_END = re.compile(r"\b(?:including|and|or|with|for|on|to|from|of|in|plus)\.?$", re.I)
DATE = re.compile(r"(?:through|until|ends?|expires?)\s+([A-Z][a-z]+\s+\d{1,2}(?:,\s*\d{4})?)", re.I)

def find_chrome():
    candidates = [
        os.environ.get("CHROME_PATH"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
    ]
    if os.name == "nt":
        candidates += [
            Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
        ]
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)

def websocket_connect(url):
    match = re.match(r"ws://([^/:]+):(\d+)(/.*)", url)
    if not match:
        raise RuntimeError("unsupported Chrome debugging URL")
    host, port, path = match.group(1), int(match.group(2)), match.group(3)
    connection = socket.create_connection((host, port), timeout=10)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\n"
        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
    )
    connection.sendall(request.encode("ascii"))
    response = b""
    while b"\r\n\r\n" not in response:
        response += connection.recv(4096)
    if b" 101 " not in response.split(b"\r\n", 1)[0]:
        connection.close()
        raise RuntimeError("Chrome debugging WebSocket upgrade failed")
    return connection

def websocket_send(connection, payload):
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = bytearray([0x81])
    if len(data) < 126:
        header.append(0x80 | len(data))
    elif len(data) < 65536:
        header.append(0x80 | 126); header.extend(struct.pack("!H", len(data)))
    else:
        header.append(0x80 | 127); header.extend(struct.pack("!Q", len(data)))
    mask = os.urandom(4); header.extend(mask)
    connection.sendall(bytes(header) + bytes(value ^ mask[index % 4] for index, value in enumerate(data)))

def websocket_receive(connection):
    def read_exact(length):
        value = b""
        while len(value) < length:
            chunk = connection.recv(length - len(value))
            if not chunk: raise RuntimeError("Chrome debugging WebSocket closed")
            value += chunk
        return value
    first, second = read_exact(2)
    opcode, length = first & 0x0F, second & 0x7F
    if length == 126: length = struct.unpack("!H", read_exact(2))[0]
    elif length == 127: length = struct.unpack("!Q", read_exact(8))[0]
    if second & 0x80: mask = read_exact(4)
    else: mask = None
    data = read_exact(length)
    if mask: data = bytes(value ^ mask[index % 4] for index, value in enumerate(data))
    if opcode == 8: raise RuntimeError("Chrome debugging WebSocket closed")
    return json.loads(data.decode("utf-8"))

def chrome_command(connection, command_id, method, params=None, timeout=20):
    websocket_send(connection, {"id": command_id, "method": method, "params": params or {}})
    connection.settimeout(timeout)
    while True:
        message = websocket_receive(connection)
        if message.get("id") == command_id:
            if message.get("error"):
                raise RuntimeError(message["error"].get("message", "Chrome command failed"))
            return message.get("result", {})

def render(url):
    chrome = find_chrome()
    if not chrome:
        raise RuntimeError("render requested but Chrome/Chromium is not installed")
    profile = tempfile.mkdtemp(prefix="truedealatlas-")
    process = None; connection = None
    try:
        command = [
            chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
            "--disable-dev-shm-usage", "--disable-background-networking",
            "--disable-component-update", "--disable-extensions", "--disable-sync",
            "--no-first-run", "--no-default-browser-check", "--incognito",
            "--user-data-dir=" + profile, "--remote-debugging-port=0", "about:blank",
        ]
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port_file = Path(profile) / "DevToolsActivePort"
        for _ in range(300):
            if port_file.exists(): break
            if process.poll() is not None: raise RuntimeError("Chrome exited before rendering")
            time.sleep(0.05)
        else: raise RuntimeError("Chrome debugging port did not start")
        port = port_file.read_text(encoding="utf-8").splitlines()[0]
        targets = json.loads(urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5).read())
        page_target = next(item for item in targets if item.get("type") == "page")
        connection = websocket_connect(page_target["webSocketDebuggerUrl"])
        chrome_command(connection, 1, "Page.enable")
        chrome_command(connection, 2, "Page.navigate", {"url": url})
        connection.settimeout(20)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if websocket_receive(connection).get("method") == "Page.loadEventFired": break
            except socket.timeout: break
        time.sleep(2)
        result = chrome_command(connection, 3, "Runtime.evaluate", {
            "expression": "document.documentElement.outerHTML",
            "returnByValue": True,
        })
        page = result.get("result", {}).get("value", "")
    finally:
        if connection:
            try: chrome_command(connection, 99, "Browser.close", timeout=3)
            except Exception: pass
            connection.close()
        if process:
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
        shutil.rmtree(profile, ignore_errors=True)
    parser = PageTextParser(); parser.feed(page)
    visible = " ".join(parser.parts)
    if re.search(r"(?:captcha|robot or human|verify you are human|press\s*&\s*hold|access denied)", visible, re.I):
        raise RuntimeError("render blocked by a human-verification or access-denied page")
    if len(visible) < 100:
        raise RuntimeError("render returned no usable page")
    return page

def fetch(url, mode="static"):
    if mode == "render":
        return render(url)
    request = Request(url, headers={
        "User-Agent": "TrueDealAtlasBot/1.1 (+https://truedealatlas.com/about.html)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
        "Accept-Language": "en-US,en;q=0.8",
        "Cache-Control": "no-cache",
    })
    with urlopen(request, timeout=30) as response:
        raw = response.read(2_000_000)
        return raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")

def clean_text(text):
    text = re.sub(r"\s+", " ", html.unescape(text)).strip(" -|:()")
    return re.sub(r"\s*\|\s*[^|]+$", "", text).strip()

def promotion_kind(text):
    for kind, pattern in (
        ("code", PROMO_CODE), ("percent", PERCENT), ("money_off", MONEY_OFF),
        ("shipping", FREE_SHIPPING), ("bogo_gift", BOGO_OR_GIFT),
        ("limited_event", LIMITED_EVENT), ("clearance_price", CLEARANCE_PRICE),
    ):
        if pattern.search(text):
            return kind
    return None

def usable_candidate(text, offer_url):
    words = text.split()
    if not 2 <= len(words) <= 32 or len(text) > 240:
        return False
    if EXCLUDED_TEXT.search(text) or EXCLUDED_PATH.search(urlparse(offer_url).path):
        return False
    if FRAGMENT_START.search(text) or FRAGMENT_END.search(text) or text.endswith(("...", ":", ";", ",")):
        return False
    if re.search(r"(?:window\.|webpack|javascript|function\s*\(|@context|errorBeacon|licenseKey|align-items:)", text, re.I):
        return False
    return promotion_kind(text) is not None

def extract_conditions(text, kind):
    code = PROMO_CODE.search(text)
    def include_code(value):
        if code and code.group(1).lower() not in value.lower():
            return value + "; Code " + code.group(1)
        return value

    percent = PERCENT.search(text)
    money_off = MONEY_OFF.search(text)
    signal = percent or money_off or FREE_SHIPPING.search(text) or BOGO_OR_GIFT.search(text)
    if signal:
        tail = re.split(r"[.!?;|]", text[signal.end():], maxsplit=1)[0].strip(" ,.-")
        tail = re.split(r"\b(?:learn more|shop now)\b", tail, maxsplit=1, flags=re.I)[0].strip(" ,.-")
        tail = re.split(r"\s+\+\s+", tail, maxsplit=1)[0].strip(" ,.-")
        if tail:
            if kind == "shipping" and re.match(r"^(?:and\b|\W+$)", tail, re.I):
                return None
            prefix = text[:signal.start()].strip(" ,.-")
            if ":" in prefix:
                eligibility = prefix.split(":", 1)[0].strip()
                if eligibility.lower() != "on now" and len(eligibility.split()) <= 6:
                    tail = eligibility + "; " + tail
            value = tail[0].upper() + tail[1:]
            if len(re.findall(r"[A-Za-z0-9$]+", value)) >= 2:
                return include_code(value)
        prefix = text[:signal.start()].strip(" ,.-")
        scope = re.search(r"\b(?:on|for)\s+([^,.;]{2,100})(?:,\s*)?$", prefix, re.I)
        if scope:
            value = scope.group(1).strip()
            return include_code(value[0].upper() + value[1:])
    if kind == "clearance_price":
        return "Clearance items only"
    if kind == "bogo_gift":
        return include_code(text)
    if kind == "limited_event":
        return text
    return None

def concise_title(text, provider, kind):
    percent = PERCENT.search(text)
    code = PROMO_CODE.search(text)
    money_off = MONEY_OFF.search(text)
    clearance = CLEARANCE_PRICE.search(text)
    if percent:
        qualifier = (percent.group(1) or "").title()
        core = "{}{}% Off".format((qualifier + " ") if qualifier else "", percent.group(2))
        tail = text[percent.end():].strip(" ,:-")
        tail = re.split(r"[.!?;|]|\b(?:also|restrictions?|terms?|save on)\b", tail, maxsplit=1, flags=re.I)[0]
        tail = re.sub(r"^with exclusive offers for\s+", "for ", tail, flags=re.I)
        tail = re.split(r"\bwith any\b", tail, maxsplit=1, flags=re.I)[0]
        tail = re.sub(r"^(?:on\s+now:?|on|for)\s+", "", tail, flags=re.I).strip(" ,:-")
        if re.match(r"^with\b", tail, re.I):
            prefix_scope = re.search(r"\b(?:save|get|take)\s+on\s+([^,.;]{2,100})(?:,\s*(?:up to)?\s*)?$", text[:percent.start()], re.I)
            if prefix_scope:
                tail = prefix_scope.group(1)
        tail = re.sub(r"\b{}\b".format(re.escape(provider)), "", tail, flags=re.I).strip()
        scope = " ".join(tail.split()[:4])
        scope = re.sub(r"\b(?:and|or|with|on|for|from|to|in|any)$", "", scope, flags=re.I).strip(" ,:+-")
        offer = core + ((" " + scope) if scope else "")
    elif money_off:
        prefix = re.search(r"\b(?:save\s+(up to)\s+|(?:get|take)\s+)?", money_off.group(0), re.I)
        offer = (("Up to ") if prefix and prefix.group(1) else "") + money_off.group(1).replace(" ", "") + " Off"
    elif kind == "shipping":
        shipping = FREE_SHIPPING.search(text)
        scope = re.split(r"[.!?;|]", text[shipping.end():], maxsplit=1)[0].strip(" ,:-")
        scope = " ".join(scope.split()[:4])
        offer = "Free Shipping" + ((" " + scope) if scope else "")
    elif kind == "clearance_price" and clearance:
        offer = "Clearance Under " + clearance.group(1).replace(" ", "")
    else:
        offer = re.split(r"[.!?;|]", text, maxsplit=1)[0].strip(" ,:-")
    if code and code.group(1).lower() not in offer.lower():
        offer += " with Code " + code.group(1).upper()
    words = offer.split()
    max_offer_words = max(2, 12 - len(provider.split()))
    if len(words) > max_offer_words:
        return None
    return f"{provider}: {offer}" if not offer.lower().startswith(provider.lower()) else offer

def dedupe_key(provider, text, kind):
    percent = PERCENT.search(text)
    code = PROMO_CODE.search(text)
    money = MONEY_OFF.search(text)
    clearance = CLEARANCE_PRICE.search(text)
    amount = (percent.group(2) + "%") if percent else (money.group(1) if money else (clearance.group(1) if clearance else ""))
    scope = extract_conditions(text, kind) or text
    scope = re.sub(r"\b(?:select|sale|items?|products?|official|now|only|the|a|an|most)\b", " ", scope, flags=re.I)
    scope = re.sub(r"\W+", " ", scope.lower()).strip()
    return provider.lower(), kind, (code.group(1).lower() if code else ""), re.sub(r"\W", "", amount.lower()), " ".join(scope.split()[:6])

def extract_offers(provider, page):
    parser = PageTextParser(); parser.feed(page)
    candidates = [(part, provider["offer_url"]) for part in parser.parts]
    candidates += [(label, urljoin(provider["offer_url"], href)) for label, href in parser.links]
    seen, seen_titles, offers = set(), set(), []
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for text, offer_url in candidates:
        text = clean_text(text)
        if not usable_candidate(text, offer_url): continue
        kind = promotion_kind(text)
        conditions = extract_conditions(text, kind)
        title = concise_title(text, provider["name"], kind)
        if not conditions or not title: continue
        key = dedupe_key(provider["name"], text, kind)
        if key in seen: continue
        title_key = re.sub(r"\W+", " ", title.lower()).strip()
        if title_key in seen_titles: continue
        seen.add(key)
        seen_titles.add(title_key)
        offer = {"provider": provider["name"], "title": title, "offer_text": text, "conditions": conditions, "offer_url": offer_url, "source_url": provider["offer_url"], "fetched_at": fetched_at, "active": True}
        percent, date_match = PERCENT.search(text), DATE.search(text)
        if percent: offer["discount_percent"] = int(percent.group(2))
        if date_match: offer["valid_until_text"] = date_match.group(1)
        offers.append(offer)
        if len(offers) >= 8: break
    return offers

def main():
    config = parse_config(); all_offers = []; provider_status = []
    for provider in config["providers"]:
        try:
            offers = extract_offers(provider, fetch(provider["offer_url"], provider.get("fetch_mode", "static")))
            all_offers.extend(offers)
            provider_status.append({"name": provider["name"], "source_url": provider["offer_url"], "fetch_mode": provider.get("fetch_mode", "static"), "status": "ok", "offer_count": len(offers)})
        except Exception as exc:
            provider_status.append({"name": provider["name"], "source_url": provider["offer_url"], "fetch_mode": provider.get("fetch_mode", "static"), "status": "error", "error": str(exc)[:300], "offer_count": 0})
        time.sleep(1)
    payload = {"generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "brand": config["meta"].get("brand", "TrueDealAtlas"), "niche": config["meta"].get("niche", "US consumer brand coupons and discounts"), "locale": config["meta"].get("locale", "en-US"), "providers": provider_status, "offers": all_offers}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(all_offers)} offers from {len(provider_status)} providers")

if __name__ == "__main__": main()
