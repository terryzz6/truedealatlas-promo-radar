import unittest

from scraper import extract_offers, parse_config


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


if __name__ == "__main__":
    unittest.main()
