import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v182" / "audience-pathways-ar.json"
SCRIPT = ROOT / "scripts" / "publish_audience_pathways_v182.py"


class AudiencePathwaysTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_exact_audience_contract(self):
        self.assertEqual([x["id"] for x in self.data["audiences"]], ["person", "family", "teacher", "student", "professional"])

    def test_resources_cover_requested_surfaces(self):
        ids = {x["id"] for x in self.data["shared_resources"]}
        self.assertEqual(ids, {"simple-explanations", "bilingual-glossary", "disability-center", "worksheets", "infographics"})

    def test_each_audience_has_depth_and_valid_links(self):
        resource_ids = {x["id"] for x in self.data["shared_resources"]}
        for item in self.data["audiences"]:
            self.assertGreaterEqual(len(item["goals"]), 3)
            self.assertGreaterEqual(len(item["first_steps"]), 4)
            self.assertGreaterEqual(len(item["avoid"]), 3)
            self.assertTrue(set(item["recommended"]).issubset(resource_ids))

    def test_disability_language_is_rights_based(self):
        text = DATA.read_text(encoding="utf-8")
        for phrase in ["كرامة", "المشاركة", "الإتاحة", "الحقوق", "موافقة"]:
            self.assertIn(phrase, text)

    def test_safety_boundaries_present(self):
        text = DATA.read_text(encoding="utf-8")
        for phrase in ["لا تقدم تشخيصًا", "خطر مباشر", "إيذاء النفس", "حماية"]:
            self.assertIn(phrase, text)

    def test_publisher_builds_metadata_schema_and_sitemap_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            subprocess.run([sys.executable, str(SCRIPT), str(site)], check=True)
            subprocess.run([sys.executable, str(SCRIPT), str(site)], check=True)
            html = (site / "for-you" / "index.html").read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', html)
            self.assertEqual(html.count("<h1>"), 1)
            for marker in ["canonical", "application/ld+json", "og:title", "twitter:title"]:
                self.assertIn(marker, html)
            for anchor in ["#person", "#family", "#teacher", "#student", "#professional"]:
                self.assertIn(anchor, html)
            tree = ET.parse(site / "sitemap.xml")
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locs = [n.text for n in tree.getroot().findall("sm:sitemap/sm:loc", ns)]
            self.assertEqual(locs.count("https://khaledaltheeb.github.io/pterminology-site/sitemap-audience-pathways.xml"), 1)
            report = json.loads((site / "api" / "audience-pathways-v182.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")
            self.assertEqual(report["audiences"], 5)


if __name__ == "__main__":
    unittest.main()
