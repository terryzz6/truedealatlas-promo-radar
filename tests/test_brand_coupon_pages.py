import html
import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from build import BASE, SITE, build, load_brand_coupon_pages


class BrandCouponPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.pages = load_brand_coupon_pages()

    def test_each_page_has_source_answer_schema_and_only_its_brand(self):
        expected = {"Hostinger", "Shopify", "Grammarly", "ActiveCampaign", "FreshBooks", "HubSpot", "monday.com", "Kit", "GetResponse", "AWeber", "Podia"}
        self.assertEqual(expected, {item["brand"] for item in self.pages})
        self.assertNotIn("Kinsta", expected)
        for item in self.pages:
            with self.subTest(brand=item["brand"]):
                path = "/guides/" + item["slug"] + ".html"
                markup = (SITE / path.lstrip("/")).read_text(encoding="utf-8")
                self.assertIn('<link rel="canonical" href="' + BASE + path.removesuffix(".html") + '">', markup)
                self.assertIn('<p class="answer"><strong>Answer:</strong> ' + html.escape(item["answer"], quote=True), markup)
                self.assertTrue(item["answer"].startswith("On 2026-09-29, no public "))
                self.assertIn("after manually reviewing", item["answer"])
                self.assertIn("official", item["answer"])
                self.assertIn("this check covers only", item["answer"])
                self.assertIn("not the entire website", item["answer"])
                self.assertIn("Reviewed 2026-09-29 &middot; Last updated 2026-09-29", markup)
                self.assertIn('"@type": "FAQPage"', markup)
                self.assertIn('<p class="brand-copyright">', markup)
                self.assertIsNone(re.search(r"[\u3400-\u9fff]", markup))
                footer = markup.split("<footer>", 1)[1]
                for other in self.pages:
                    self.assertEqual(other["brand"] in footer, other is item)
                for offer in item["offers"]:
                    self.assertIn(offer["source"], markup)
                    self.assertEqual("2026-09-29", offer["checked"])
                    self.assertIn(offer["end_date"], {"No offer-specific end date found. Not finding one does not mean the offer is permanent.", "No expiration date.", "Free forever."})
                    self.assertIn(offer["checked"], markup)
                    self.assertIn(offer["end_date"], markup)
                dated_faq = next(q for q in item["faq"] if "code" in q["question"].lower())
                self.assertIn("2026-09-29", dated_faq["answer"])

    def test_new_pages_include_keyword_variants_and_bidirectional_links(self):
        expected_terms = {
            "hubspot-coupon": ("HubSpot Coupon", "Promo Code", "Discount Code"),
            "monday-coupon": ("monday Coupon", "Promo Code", "Discount Code"),
            "kit-discount-code": ("Kit Discount Code", "Coupon", "Promo Code"),
            "getresponse-coupon": ("GetResponse Coupon", "Promo Code", "Discount Code"),
            "aweber-coupon": ("AWeber Coupon", "Promo Code", "Discount Code"),
            "podia-coupon": ("Podia Coupon", "Promo Code", "Discount Code"),
        }
        directory = (SITE / "guides" / "index.html").read_text(encoding="utf-8")
        for item in self.pages:
            if item["slug"] not in expected_terms:
                continue
            with self.subTest(brand=item["brand"]):
                markup = (SITE / "guides" / (item["slug"] + ".html")).read_text(encoding="utf-8")
                for term in expected_terms[item["slug"]]:
                    self.assertIn(term, item["title"])
                    self.assertIn(term.lower(), markup.lower())
                self.assertIn('href="/guides/"', markup)
                self.assertIn('href="/guides/' + item["slug"] + '"', directory)

    def test_sitemap_has_one_entry_per_brand_with_check_date(self):
        root = ET.parse(SITE / "sitemap.xml").getroot()
        entries = {node.findtext("{*}loc"): node.findtext("{*}lastmod") for node in root}
        for item in self.pages:
            url = BASE + "/guides/" + item["slug"]
            self.assertEqual(item["updated"], entries[url])

    def test_guide_directory_is_sorted_by_publish_date_newest_first(self):
        root = Path(__file__).resolve().parents[1]
        articles = json.loads((root / "data" / "articles.json").read_text(encoding="utf-8"))["articles"]
        dated_slugs = [(item["published_at"], item["slug"]) for item in articles]
        dated_slugs.extend((item["updated"], item["slug"]) for item in self.pages)
        expected = [slug for _, slug in sorted(dated_slugs, key=lambda entry: entry[0], reverse=True)]

        markup = (SITE / "guides" / "index.html").read_text(encoding="utf-8")
        directory = markup.split('<ul class="provider-list">', 1)[1].split("</ul>", 1)[0]
        actual = re.findall(r'href="/guides/([^".]+)(?:\.html)?"', directory)

        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
