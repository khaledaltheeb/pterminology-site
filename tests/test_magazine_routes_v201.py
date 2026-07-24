import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_magazine_v201.py"
SOURCE_SITEMAP = ROOT / "sitemap.xml"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
URL = BASE + "/magazine/"


class MagazineRoutesV201Tests(unittest.TestCase):
    def fixture(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="magazine-v201-"))
        shutil.copy2(SOURCE_SITEMAP, site / "sitemap.xml")
        self.addCleanup(shutil.rmtree, site, True)
        return site

    def test_magazine_methodology_is_complete_and_honest(self):
        site = self.fixture()
        subprocess.run(["python3", str(PUBLISHER), str(site)], cwd=ROOT, check=True, capture_output=True, text=True)
        page = site / "magazine" / "index.html"
        self.assertTrue(page.is_file())
        text = page.read_text(encoding="utf-8")
        self.assertIn('<html lang="ar" dir="rtl">', text)
        self.assertEqual(text.count("<h1>"), 1)
        self.assertIn(f'<link rel="canonical" href="{URL}">', text)
        self.assertIn("هذه الصفحة تنشر المنهج والعقد التحريري فقط", text)
        self.assertIn("لا يتضمن هذا الإصدار ملخصات دراسات منفردة", text)
        self.assertNotIn("مراجعة اختصاصية مكتملة", text)
        report = json.loads((site / "api" / "magazine-v201.json").read_text(encoding="utf-8"))
        self.assertTrue(report["methodology_published"])
        self.assertEqual(report["research_summaries_published"], 0)
        self.assertEqual(report["review_status"], "internally-reviewed")
        self.assertEqual(report["risk_level"], "low")

    def test_magazine_sitemap_is_idempotent(self):
        site = self.fixture()
        for _ in range(2):
            subprocess.run(["python3", str(PUBLISHER), str(site)], cwd=ROOT, check=True, capture_output=True, text=True)
        child = ET.parse(site / "sitemap-magazine.xml").getroot()
        urls = [(node.text or "").strip() for node in child.findall("{*}url/{*}loc")]
        self.assertEqual(urls, [URL])
        main = ET.parse(site / "sitemap.xml").getroot()
        kind = main.tag.rsplit("}", 1)[-1]
        if kind == "urlset":
            values = [(node.text or "").strip() for node in main.findall("{*}url/{*}loc")]
            self.assertEqual(values.count(URL), 1)
        else:
            values = [(node.text or "").strip() for node in main.findall("{*}sitemap/{*}loc")]
            self.assertEqual(values.count(BASE + "/sitemap-magazine.xml"), 1)

    def test_pipeline_restores_existing_assessment_demo(self):
        pipeline = (ROOT / "scripts" / "apply_homepage_v20.py").read_text(encoding="utf-8")
        self.assertIn('restore_static_route("provider-assessment-demo")', pipeline)
        self.assertIn('run_publisher("publish_magazine_v201.py")', pipeline)
        self.assertIn('"magazine_publisher": 201', pipeline)
        required = [
            ROOT / "provider-assessment-demo" / "index.html",
            ROOT / "provider-assessment-demo" / "styles.css",
            ROOT / "provider-assessment-demo" / "catalog.js",
            ROOT / "provider-assessment-demo" / "app.js",
        ]
        self.assertTrue(all(path.is_file() for path in required))


if __name__ == "__main__":
    unittest.main()
