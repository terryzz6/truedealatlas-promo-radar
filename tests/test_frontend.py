import unittest

from build import coupon_code, format_checked, offer_card, offer_kind, offer_saving


class CouponPresentationTests(unittest.TestCase):
    def test_percent_qualifiers_are_not_lost(self):
        for text, expected in (("Up to 40% off shoes", "Up to 40% off"), ("Extra 40% off sale", "Extra 40% off"), ("BOGO 40% off select skin care", "BOGO 40% off")):
            with self.subTest(text=text):
                self.assertEqual(expected, offer_saving({"offer_text": text, "discount_percent": 40}))

    def test_codes_are_taken_only_from_official_offer_text(self):
        self.assertEqual("SAVE20", coupon_code({"offer_text": "Use Code SAVE20 for 20% off"}))
        self.assertEqual("", coupon_code({"offer_text": "Sale on winter coats", "title": "Use code INVENTED"}))
        self.assertEqual("codes", offer_kind({"offer_text": "Free shipping with code SHIP50"}))

    def test_non_percent_savings_do_not_show_an_empty_percent(self):
        self.assertEqual("$100 off", offer_saving({"offer_text": "$100 off select computers"}))
        self.assertEqual("Free shipping", offer_saving({"offer_text": "Free shipping on $50+"}))
        self.assertEqual("Store offer", offer_saving({"offer_text": "Limited time sale"}))

    def test_missing_date_does_not_claim_recent_verification(self):
        self.assertEqual("Check date unavailable", format_checked(None))

    def test_source_terms_and_unsafe_text_are_preserved_as_text(self):
        card = offer_card({"provider": "Example", "title": "Example: 20% Off", "offer_text": 'Members only <script>bad()</script>', "conditions": "Members only", "offer_url": "https://example.com/sale", "fetched_at": "2026-09-28T01:00:00+00:00"})
        self.assertIn("Members only &lt;script&gt;bad()&lt;/script&gt;", card)
        self.assertNotIn("<script>bad()", card)
        self.assertIn("Source checked Sep 28, 2026", card)
        self.assertNotIn("Verified", card)


if __name__ == "__main__":
    unittest.main()
