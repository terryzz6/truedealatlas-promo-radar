import unittest
import json
from datetime import date
from pathlib import Path

from tools.daily_article import queue_exhausted, select_next


class DailyArticleSelectionTests(unittest.TestCase):
    def test_selects_only_the_first_due_article(self):
        queue = [
            {"slug": "first", "publish_on": "2026-09-29"},
            {"slug": "second", "publish_on": "2026-09-29"},
        ]

        selected = select_next(queue, set(), date(2026, 9, 29))

        self.assertEqual("first", selected["slug"])

    def test_future_schedule_blocks_unscheduled_backlog(self):
        queue = [
            {"slug": "tomorrow", "publish_on": "2026-09-30"},
            {"slug": "backlog"},
        ]

        selected = select_next(queue, set(), date(2026, 9, 29))

        self.assertIsNone(selected)

    def test_invalid_publish_date_fails_closed(self):
        queue = [{"slug": "bad", "publish_on": "tomorrow"}]

        with self.assertRaisesRegex(ValueError, "invalid publish_on for bad"):
            select_next(queue, set(), date(2026, 9, 29))

    def test_exhausted_queue_is_distinct_from_future_work(self):
        queue = [{"slug": "published"}, {"slug": "tomorrow", "publish_on": "2026-10-08"}]

        self.assertTrue(queue_exhausted(queue[:1], {"published"}))
        self.assertFalse(queue_exhausted(queue, {"published"}))

    def test_unpublished_queue_stays_in_locked_word_pool(self):
        root = Path(__file__).resolve().parents[1]
        queue = json.loads((root / "data" / "editorial_queue.json").read_text(encoding="utf-8"))
        articles = json.loads((root / "data" / "articles.json").read_text(encoding="utf-8"))["articles"]
        published = {item["slug"] for item in articles}
        allowed = {
            "old-navy-promo-code",
            "old-navy-coupon-code",
            "old-navy-discount-code",
            "old-navy-coupons-in-store",
            "old-navy-promo-code-today",
            "old-navy-promo",
            "old-navy-free-shipping-code",
            "old-navy-super-cash",
            "old-navy-rewards-program",
            "old-navy-birthday-bonus",
            "old-navy-member-free-shipping",
            "old-navy-super-cash-stacking",
        }

        unpublished = {item["slug"] for item in queue if item["slug"] not in published}

        self.assertLessEqual(unpublished, allowed)


if __name__ == "__main__":
    unittest.main()
