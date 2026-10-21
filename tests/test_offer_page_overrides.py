import html
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from build import BASE, SITE, build, redirect_target


class OfferPageOverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build()
        cls.overrides = json.loads((Path(__file__).resolve().parents[1] / "data" / "offer_page_overrides.json").read_text(encoding="utf-8"))
        cls.urls = {entry.findtext("{*}loc") for entry in ET.parse(SITE / "sitemap.xml").getroot()}

    def test_redirected_pages_leave_sitemap_and_have_301_rules(self):
        rules = (SITE / "_redirects").read_text(encoding="utf-8").splitlines()
        self.assertEqual(8, len(rules))
        for source, target in self.overrides["redirects"].items():
            with self.subTest(source=source):
                self.assertIn(f"{source} {target} 301", rules)
                self.assertNotIn(BASE + source, self.urls)
                self.assertFalse((SITE / source.lstrip("/")).exists())
                self.assertIn(BASE + target, self.urls)

    def test_titles_use_full_source_text_without_changing_paths(self):
        for path, override in self.overrides["pages"].items():
            with self.subTest(path=path):
                markup = (SITE / path.lstrip("/")).read_text(encoding="utf-8")
                self.assertIn(BASE + path, self.urls)
                self.assertIn(f"<h1>{html.escape(override['title'].split(': ', 1)[1])}</h1>", markup)
        for percent in (71, 73, 84):
            self.assertTrue(any(f"/deals/nordstrom-rack-nordstrom-rack-up-to-{percent}-off-" in url for url in self.urls))

    def test_missing_target_redirects_to_the_store(self):
        source="/deals/old-navy-old-navy-60-off-steals-baby-girls.html"
        target=self.overrides["redirects"][source]
        self.assertEqual("/providers/old-navy.html",redirect_target(source,target,set()))


if __name__ == "__main__":
    unittest.main()
