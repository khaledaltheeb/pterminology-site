import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v161" / "blog-anxiety-ar.json"
PUBLISHER = ROOT / "scripts" / "publish_blog_v161.py"
FINALIZER = ROOT / "scripts" / "finalize_blog_links_v161.py"
APPLIER = ROOT / "scripts" / "apply_homepage_v20.py"
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)
SOURCE_FIELDS = {"id", "publisher", "title", "url", "year", "source_type", "verified_at", "claims_supported", "status"}


class ArabicBlogV161Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATA.read_text(encoding="utf-8"))
        cls.article = cls.payload["articles"][0]

    def test_article_depth_review_and_safety_boundaries(self):
        article = self.article
        text = " ".join(
            paragraph
            for section in article["sections"]
            for paragraph in section["paragraphs"]
        )
        self.assertGreaterEqual(len(article["sections"]), 7)
        self.assertGreaterEqual(len(WORD_RE.findall(text)), 650)
        self.assertEqual(article["status"], "reviewed")
        self.assertEqual(article["review_status"], "internally-reviewed")
        self.assertEqual(article["risk_level"], "high")
        self.assertGreaterEqual(len(article["related"]), 3)
        for forbidden in ("غيّر جرعتك", "أوقف الدواء", "تشخيص مؤكد", "علاج مضمون"):
            self.assertNotIn(forbidden, text)

    def test_sources_are_unique_contract_ready_and_claim_specific(self):
        sources = self.article["sources"]
        self.assertGreaterEqual(len(sources), 3)
        self.assertEqual(len({source["id"] for source in sources}), len(sources))
        self.assertEqual(len({source["url"] for source in sources}), len(sources))
        for source in sources:
            self.assertTrue(SOURCE_FIELDS <= set(source), SOURCE_FIELDS - set(source))
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIsInstance(source["year"], int)
            self.assertLessEqual(source["year"], 2026)
            self.assertTrue(source["claims_supported"])
            self.assertEqual(source["status"], "current")

    def test_publisher_outputs_article_index_sitemap_and_truthful_report(self):
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            (site / "index.html").write_text((ROOT / "index.html").read_text(encoding="utf-8"), encoding="utf-8")
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
                encoding="utf-8",
            )
            subprocess.run([sys.executable, str(PUBLISHER), str(site)], check=True)
            subprocess.run([sys.executable, str(FINALIZER), str(site)], check=True)
            subprocess.run([sys.executable, str(FINALIZER), str(site)], check=True)

            article_path = site / "blog" / self.article["slug"] / "index.html"
            blog_index = site / "blog" / "index.html"
            self.assertTrue(article_path.is_file())
            self.assertTrue(blog_index.is_file())
            article_html = article_path.read_text(encoding="utf-8")
            self.assertEqual(article_html.count("<h1>"), 1)
            self.assertIn('rel="canonical"', article_html)
            self.assertIn('application/ld+json', article_html)
            for source in self.article["sources"]:
                self.assertIn(source["url"], article_html)
                self.assertIn(source["publisher"], article_html)

            report = json.loads((site / "api" / "blog-v161.json").read_text(encoding="utf-8"))
            self.assertEqual(report["articles"], len(self.payload["articles"]))
            self.assertEqual(report["source_records"], len(self.article["sources"]))
            self.assertEqual(report["unique_source_ids"], report["source_records"])
            self.assertTrue(report["source_contract_ready"])

            ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            blog_tree = ET.parse(site / "sitemap-blog.xml")
            blog_urls = [node.text for node in blog_tree.findall("s:url/s:loc", ns)]
            self.assertEqual(len(blog_urls), 2)
            main_tree = ET.parse(site / "sitemap.xml")
            main_urls = [node.text for node in main_tree.findall("s:sitemap/s:loc", ns)]
            self.assertEqual(main_urls.count("https://khaledaltheeb.github.io/pterminology-site/sitemap-blog.xml"), 1)

            home = (site / "index.html").read_text(encoding="utf-8")
            self.assertEqual(home.count('<a href="blog/">المدونة</a>'), 1)
            self.assertEqual(home.count("المدونة التحليلية"), 1)

    def test_homepage_pipeline_preserves_existing_publishers_then_adds_blog(self):
        text = APPLIER.read_text(encoding="utf-8")
        ordered = [
            'run_publisher("publish_care_guides_v21.py")',
            'run_publisher("publish_special_needs_v73.py")',
            'run_publisher("publish_blog_v161.py")',
            'run_publisher("finalize_blog_links_v161.py")',
            'run_publisher("publish_homepage_i18n_v72.py")',
        ]
        positions = [text.index(marker) for marker in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('"blog_publisher": 161', text)


if __name__ == "__main__":
    unittest.main()
