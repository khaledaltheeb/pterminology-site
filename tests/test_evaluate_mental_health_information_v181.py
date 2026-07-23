import json
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

import scripts.publish_evaluate_mental_health_information_v181 as publisher


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v181" / "evaluate-mental-health-information-ar.json"


class EvaluateMentalHealthInformationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_content_depth_sources_and_safety(self):
        text = " ".join(
            [self.data["summary"]]
            + [p for section in self.data["sections"] for p in section["paragraphs"]]
            + self.data["decision_checklist"]
            + self.data["red_flags"]
        )
        self.assertGreaterEqual(len(text.split()), 700)
        self.assertGreaterEqual(len(self.data["sections"]), 8)
        self.assertGreaterEqual(len(self.data["sources"]), 3)
        self.assertEqual(len({s["id"] for s in self.data["sources"]}), len(self.data["sources"]))
        self.assertTrue(all(s["url"].startswith("https://") for s in self.data["sources"]))
        for forbidden in ["شفاء مضمون", "أوقف الدواء", "غيّر الجرعة", "تشخيص مؤكد"]:
            self.assertNotIn(forbidden, text)

    def test_metadata_schema_and_accessibility(self):
        html = publisher.render()
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup.html.get("lang"), "ar")
        self.assertEqual(soup.html.get("dir"), "rtl")
        self.assertEqual(len(soup.find_all("h1")), 1)
        self.assertTrue(soup.find("meta", attrs={"name": "description"})["content"])
        self.assertEqual(soup.find("link", rel="canonical")["href"], f"{publisher.BASE}{publisher.ROUTE}")
        self.assertIsNotNone(soup.find("a", class_="skip"))
        graph = json.loads(soup.find("script", attrs={"type": "application/ld+json"}).string)["@graph"]
        self.assertEqual({item["@type"] for item in graph}, {"Article", "BreadcrumbList"})
        article = next(item for item in graph if item["@type"] == "Article")
        self.assertEqual(len(article["citation"]), len(self.data["sources"]))

    def test_build_outputs_are_explicitly_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_site = publisher.SITE
            try:
                publisher.SITE = Path(tmp)
                publisher.main()
            finally:
                publisher.SITE = old_site
            page = Path(tmp) / "evaluate-mental-health-information" / "index.html"
            report = json.loads((Path(tmp) / "api" / "evaluate-mental-health-information-v181.json").read_text(encoding="utf-8"))
            self.assertTrue(page.is_file())
            self.assertEqual(report["status"], "built-not-published")
            sitemap = ET.parse(Path(tmp) / "sitemap-evaluate-mental-health-information.xml")
            loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            self.assertEqual(loc.text, f"{publisher.BASE}{publisher.ROUTE}")

    def test_internal_links_are_unique_and_section_relevant(self):
        hrefs = [item["href"] for item in self.data["related_links"]]
        self.assertEqual(len(hrefs), len(set(hrefs)))
        self.assertIn("/editorial-methodology/", hrefs)
        self.assertIn("/encyclopedia/", hrefs)
        self.assertIn("/special-needs/", hrefs)


if __name__ == "__main__":
    unittest.main()
