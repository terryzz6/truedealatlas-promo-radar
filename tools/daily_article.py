import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "editorial_queue.json"
ARTICLES = ROOT / "data" / "articles.json"
SITE_TZ = ZoneInfo("America/Los_Angeles")


def select_next(queue, published, today):
    unpublished = [item for item in queue if item.get("slug") not in published]

    def publish_date(item):
        publish_on = item.get("publish_on")
        if not publish_on:
            return None
        try:
            return datetime.fromisoformat(publish_on).date()
        except (TypeError, ValueError):
            raise ValueError(f"invalid publish_on for {item.get('slug')}: {publish_on}")

    dated = [(item, publish_date(item)) for item in unpublished]
    due_items = [item for item, publish_on in dated if publish_on is not None and publish_on <= today]
    if due_items:
        return due_items[0]
    if any(publish_on is not None and publish_on > today for _, publish_on in dated):
        return None
    return next((item for item, publish_on in dated if publish_on is None), None)


def queue_exhausted(queue, published):
    return not any(item.get("slug") not in published for item in queue)


def main():
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    payload = json.loads(ARTICLES.read_text(encoding="utf-8")) if ARTICLES.exists() else {"articles": []}
    articles = payload.setdefault("articles", [])
    published = {item.get("slug") for item in articles}
    now = datetime.now(SITE_TZ)
    today = now.date()

    next_item = select_next(queue, published, today)
    if next_item is None:
        if queue_exhausted(queue, published):
            print("editorial_queue=exhausted")
            raise SystemExit(1)
        print("editorial_queue=no_due_item")
        return
    item = dict(next_item)
    item["published_at"] = today.isoformat()
    item.pop("publish_on", None)
    articles.append(item)
    ARTICLES.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"published={item['slug']}")


if __name__ == "__main__":
    main()
