import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v182" / "privacy-mental-health-tools-ar.json"
PUBLISHER = ROOT / "scripts" / "publish_privacy_mental_health_tools_v182.py"

spec = importlib.util.spec_from_file_location("privacy_v182", PUBLISHER)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


class PrivacyMentalHealthToolsV182Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTENT.read_text(encoding="utf-8"))

    def test_content_is_deep_original_and_safely_bounded(self):
        text = " ".join(
            paragraph
            for section in self.data["sections"]
            for paragraph in section["paragraphs"]
        )
        self.assertGreaterEqual(len(self.data["sections"]), 9)
        self.assertGreaterEqual(len(text.split()), 700)
        for phrase in [
            "التخزين المحلي",
            "سياسة الخصوصية",
            "التصدير والحذف",
            "طفل",
            "ليس استشارة قانونية",
            "مساعدة طارئة محلية",
        ]:
            self.assertIn(phrase, text)
        prohibited = ["يشخّص", "يعالج نهائيًا", "آمن تمامًا", "مضمون", "استبدل دواءك"]
        for phrase in prohibited:
            self.assertNotIn(phrase, text)

    def test_sources_follow_repository_evidence_shape(self):
        required = {
            "id", "source_type", "title", "publisher", "year", "url",
            "verified_at", "claims_supported", "status"
        }
        ids = set()
        for source in self.data["sources"]:
            self.assertFalse(required - set(source))
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIn(source["source_type"], {"public_health_authority", "institutional_fact_sheet"})
            self.assertEqual(source["status"], "current")
            self.assertTrue(source["claims_supported"])
            self.assertNotIn(source["id"], ids)
            ids.add(source["id"])
        self.assertGreaterEqual(len(ids), 4)

    def test_rendered_page_has_complete_seo_schema_rtl_and_links(self):
        page = module.render_page(self.data)
        soup = BeautifulSoup(page, "html.parser")
        self.assertEqual(soup.html.get("lang"), "ar")
        self.assertEqual(soup.html.get("dir"), "rtl")
        self.assertEqual(len(soup.find_all("h1")), 1)
        self.assertTrue(soup.find("meta", attrs={"name": "description"}).get("content"))
        self.assertEqual(soup.find("link", attrs={"rel": "canonical"}).get("href"), module.CANONICAL)
        self.assertIsNotNone(soup.find("meta", attrs={"property": "og:title"}))
        self.assertIsNotNone(soup.find("meta", attrs={"name": "twitter:card"}))
        schema = json.loads(soup.find("script", attrs={"type": "application/ld+json"}).string)
        self.assertEqual({item["@type"] for item in schema}, {"Article", "BreadcrumbList"})
        internal = [a.get("href") for a in soup.find_all("a") if str(a.get("href", "")).startswith("/")]
        for expected in ["/start-here/", "/assessments/", "/daily-tools/", "/special-needs/"]:
            self.assertIn(expected, internal)

    def test_build_outputs_page_sitemap_and_explicit_nonpublication_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = module.build(root)
            page = root / "care-guides" / self.data["slug"] / "index.html"
            sitemap = root / "sitemap-privacy-mental-health-tools.xml"
            api = root / "api" / "privacy-mental-health-tools-v182.json"
            self.assertTrue(page.is_file())
            self.assertTrue(sitemap.is_file())
            self.assertTrue(api.is_file())
            self.assertEqual(report["status"], "built-not-published")
            self.assertEqual(report["sources"], len(self.data["sources"]))
            self.assertEqual(sitemap.read_text(encoding="utf-8").count(module.CANONICAL), 1)
            stored = json.loads(api.read_text(encoding="utf-8"))
            self.assertEqual(stored["status"], "built-not-published")

    def test_internal_links_are_unique_and_cross_sectional(self):
        hrefs = [item["href"] for item in self.data["internal_links"]]
        self.assertEqual(len(hrefs), len(set(hrefs)))
        self.assertGreaterEqual(len(hrefs), 6)
        prefixes = {href.split("/")[1] for href in hrefs if href.startswith("/") and len(href.split("/")) > 1}
        self.assertGreaterEqual(len(prefixes), 5)


if __name__ == "__main__":
    unittest.main()
