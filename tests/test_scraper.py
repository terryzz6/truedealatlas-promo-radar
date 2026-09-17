import tempfile
import unittest
from pathlib import Path

from build import provider_result_message
from scraper import collect_offers, extract_offers, load_previous_payload, parse_config


class OfferExtractionTests(unittest.TestCase):
    provider = {
        "name": "Example Brand",
        "offer_url": "https://example.com/sale",
    }

    def extract(self, *parts):
        return extract_offers(self.provider, "".join(f"<p>{part}</p>" for part in parts))

    def test_fetch_modes_come_from_site_config(self):
        providers = {item["name"]: item for item in parse_config()["providers"]}
        self.assertEqual("render", providers["Target"]["fetch_mode"])
        self.assertEqual("render", providers["Lenovo"]["fetch_mode"])
        self.assertEqual("static", providers["Gap"]["fetch_mode"])

    def test_rejects_policy_and_fragment_text(self):
        offers = self.extract(
            "Terms of Sale",
            "Rewards Loyalty Program",
            "offer versatility with a shirt and loafers for a polished outfit",
        )
        self.assertEqual([], offers)

    def test_keeps_one_human_title_for_near_duplicate_discount(self):
        offers = self.extract(
            "75% Off Select Items",
            "75% Off Select Sale Items",
            "75% Off Select Items | Example Brand",
        )
        self.assertEqual(1, len(offers))
        self.assertEqual("Example Brand: 75% Off Select Items", offers[0]["title"])
        self.assertEqual("Select Items", offers[0]["conditions"])

    def test_keeps_code_and_shipping_with_conditions(self):
        offers = self.extract(
            "Use code SAVE20 for 20% off select home items",
            "Free shipping on $50+ for members",
        )
        self.assertEqual(2, len(offers))
        self.assertTrue(all(len(item["title"].split()) <= 12 for item in offers))
        self.assertTrue(all(item["offer_text"] and item["conditions"] for item in offers))

    def test_rejects_shipping_chrome_and_deduplicates_scope(self):
        offers = self.extract(
            "Free shipping and easy returns",
            "Free shipping on accessories",
            "Free shipping on most accessories",
            "Free shipping ^^^",
        )
        self.assertEqual(1, len(offers))
        self.assertEqual("Example Brand: Free Shipping on accessories", offers[0]["title"])

    def test_titles_do_not_end_mid_condition(self):
        offers = self.extract(
            "Save on trusted Example Brand Refurbished tech, up to 60% off with warranty",
            "Save up to 30% off with exclusive offers for students and teachers.",
            "Extra 50% off AW5625P Backpack with any laptop purchase",
        )
        self.assertEqual(
            [
                "Example Brand: Up To 60% Off trusted Refurbished tech",
                "Example Brand: Up To 30% Off students and teachers",
                "Example Brand: Extra 50% Off AW5625P Backpack",
            ],
            [offer["title"] for offer in offers],
        )

    def test_rejects_incomplete_tail_and_keeps_bare_code(self):
        offers = self.extract(
            "Score 50% off the biggest brands in beauty, including",
            "30% off your purchase. Code YOURS",
        )
        self.assertEqual(1, len(offers))
        self.assertEqual("Example Brand: 30% Off your purchase with Code YOURS", offers[0]["title"])
        self.assertEqual("Your purchase; Code YOURS", offers[0]["conditions"])


class PipelineStateTests(unittest.TestCase):
    provider = {
        "name": "Example Brand",
        "website": "https://example.com",
        "offer_url": "https://example.com/sale",
        "fetch_mode": "static",
    }

    def run_pipeline(self, responses, previous_offers=None):
        calls = []

        def fake_fetch(url, mode):
            calls.append((url, mode))
            response = responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response

        offers, statuses = collect_offers(
            {"providers": [self.provider]},
            {"offers": previous_offers or []},
            fetcher=fake_fetch,
            sleeper=lambda _: None,
            delay=0,
        )
        return offers, statuses[0], calls

    def test_failed_provider_retains_prior_offer_and_timestamp(self):
        prior = {
            "provider": "Example Brand",
            "title": "Example Brand: 20% Off Select Items",
            "offer_text": "20% off select items",
            "conditions": "Select items",
            "offer_url": "https://example.com/sale",
            "source_url": "https://example.com/sale",
            "fetched_at": "2026-09-16T01:02:03+00:00",
            "active": True,
        }
        offers, status, calls = self.run_pipeline(
            [RuntimeError("first failure"), RuntimeError("second failure")],
            [prior],
        )
        self.assertEqual([prior], offers)
        self.assertEqual("2026-09-16T01:02:03+00:00", offers[0]["fetched_at"])
        self.assertEqual("unavailable", status["result"])
        self.assertEqual("second failure", status["error"])
        self.assertEqual(2, status["attempts"])
        self.assertEqual(1, status["retained_offer_count"])
        self.assertEqual(2, len(calls))

    def test_successful_empty_provider_removes_prior_offer(self):
        prior = {"provider": "Example Brand", "fetched_at": "unchanged"}
        page = "<html><body><p>{}</p></body></html>".format("No promotions today. " * 10)
        offers, status, _ = self.run_pipeline([page], [prior])
        self.assertEqual([], offers)
        self.assertEqual("empty", status["result"])
        self.assertEqual(1, status["attempts"])

    def test_retry_success_uses_fresh_offers(self):
        page = "<p>25% off select jackets</p><p>{}</p>".format("Official sale collection. " * 6)
        offers, status, calls = self.run_pipeline([RuntimeError("temporary"), page])
        self.assertEqual(1, len(offers))
        self.assertEqual("offers", status["result"])
        self.assertEqual(2, status["attempts"])
        self.assertEqual(2, len(calls))

    def test_challenge_page_retains_prior_offer(self):
        prior = {"provider": "Example Brand", "fetched_at": "original"}
        challenge = "<html><body><h1>Just a moment...</h1><p>Verifying your connection before proceeding.</p></body></html>"
        offers, status, _ = self.run_pipeline([challenge, challenge], [prior])
        self.assertEqual([prior], offers)
        self.assertEqual("unavailable", status["result"])
        self.assertEqual("source returned a challenge or access-denied page", status["error"])

    def test_load_previous_payload_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = load_previous_payload(Path(directory) / "missing.json")
        self.assertEqual({"offers": [], "providers": []}, payload)

    def test_provider_messages_distinguish_empty_from_unavailable(self):
        self.assertIn("not retrieved", provider_result_message({"result": "unavailable"}, True))
        self.assertIn("retrieved successfully", provider_result_message({"result": "empty"}, False))
        self.assertEqual("", provider_result_message({"result": "offers"}, True))


if __name__ == "__main__":
    unittest.main()
