import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "editorial_queue.json"
ARTICLES = ROOT / "data" / "articles.json"


def main():
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    payload = json.loads(ARTICLES.read_text(encoding="utf-8")) if ARTICLES.exists() else {"articles": []}
    articles = payload.setdefault("articles", [])
    published = {item.get("slug") for item in articles}
    next_item = next((item for item in queue if item.get("slug") not in published), None)
    if next_item is None:
        print("editorial_queue=empty")
        return
    item = dict(next_item)
    item["published_at"] = datetime.now(timezone.utc).date().isoformat()
    articles.append(item)
    ARTICLES.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"published={item['slug']}")


if __name__ == "__main__":
    main()
