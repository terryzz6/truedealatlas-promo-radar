import html
import re
import unittest
import xml.etree.ElementTree as ET

from build import BASE, SITE, build, load_brand_coupon_pages


class BrandCouponPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.pages = load_brand_coupon_pages()

    def test_each_page_has_source_answer_schema_and_only_its_brand(self):
        self.assertEqual(5, len(self.pages))
        for item in self.pages:
            with self.subTest(brand=item["brand"]):
                path = "/guides/" + item["slug"] + ".html"
                markup = (SITE / path.lstrip("/")).read_text(encoding="utf-8")
                self.assertIn('<link rel="canonical" href="' + BASE + path.removesuffix(".html") + '">', markup)
                self.assertIn('<p class="answer"><strong>Answer:</strong> ' + html.escape(item["answer"], quote=True), markup)
                self.assertIn('"@type": "FAQPage"', markup)
                self.assertIn('<p class="brand-copyright">', markup)
                self.assertIsNone(re.search(r"[\u3400-\u9fff]", markup))
                footer = markup.split("<footer>", 1)[1]
                for other in self.pages:
                    self.assertEqual(other["brand"] in footer, other is item)
                for offer in item["offers"]:
                    self.assertIn(offer["source"], markup)
                    self.assertIn(offer["checked"], markup)

    def test_sitemap_has_one_entry_per_brand_with_check_date(self):
        root = ET.parse(SITE / "sitemap.xml").getroot()
        entries = {node.findtext("{*}loc"): node.findtext("{*}lastmod") for node in root}
        for item in self.pages:
            url = BASE + "/guides/" + item["slug"]
            self.assertEqual(item["offers"][0]["checked"], entries[url])


if __name__ == "__main__":
    unittest.main()
