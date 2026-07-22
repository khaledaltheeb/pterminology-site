import json
import tempfile
import unittest
from pathlib import Path
from subprocess import run
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class WomenCenterTests(unittest.TestCase):
    def test_source_contract(self):
        data = json.loads(
            (ROOT / "content" / "v165" / "women-mental-health-ar.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["version"], 165)
        self.assertEqual(data["center"]["review_status"], "needs-specialist-review")
        self.assertEqual(data["pillar"]["review_status"], "needs-specialist-review")
        self.assertGreaterEqual(len(data["pillar"]["sections"]), 10)
        self.assertGreaterEqual(len(data["pillar"]["sources"]), 3)
        for block in (data["center"], data["pillar"]):
            for source in block["sources"]:
                self.assertTrue(source["url"].startswith("https://"))
                self.assertTrue(source["verified_at"])

    def test_publish_metadata_content_links_and_sitemap(self):
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            (site / "index.html").write_text(
                '<html lang="ar" dir="rtl"><main><h1>الرئيسية</h1></main></html>',
                encoding="utf-8",
            )
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
                encoding="utf-8",
            )
            run(
                ["python", str(ROOT / "scripts" / "publish_women_center_v165.py"), str(site)],
                check=True,
            )
            pages = [
                site / "women" / "index.html",
                site / "women" / "perinatal-mental-health" / "index.html",
            ]
            for page in pages:
                text = page.read_text(encoding="utf-8")
                self.assertIn('<html lang="ar" dir="rtl">', text)
                self.assertEqual(text.count("<h1>"), 1)
                self.assertIn('rel="canonical"', text)
                self.assertIn("application/ld+json", text)
                self.assertIn("twitter:card", text)
                self.assertTrue(
                    "غير تشخيص" in text or "دون تشخيص" in text or "لا يشخّص" in text
                )
                self.assertGreater(len(text), 5000)
            self.assertIn(
                "/pterminology-site/women/",
                (site / "index.html").read_text(encoding="utf-8"),
            )
            root = ET.parse(site / "sitemap-women.xml").getroot()
            self.assertEqual(len(root), 2)
            report = json.loads(
                (site / "api" / "women-center-v165.json").read_text(encoding="utf-8")
            )
            self.assertEqual(report["pages"], 2)
            self.assertEqual(report["sources"], 6)

    def test_no_dangerous_or_exaggerated_claims(self):
        text = (
            ROOT / "content" / "v165" / "women-mental-health-ar.json"
        ).read_text(encoding="utf-8")
        for phrase in [
            "يشخص حالتك",
            "علاج نهائي",
            "مضمون 100%",
            "أوقفي الدواء",
            "ابدئي الدواء",
        ]:
            self.assertNotIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
