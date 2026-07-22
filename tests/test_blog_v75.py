import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_blog_v75.py"
FINALIZER = ROOT / "scripts" / "finalize_blog_links_v75.py"
DATA = ROOT / "content" / "v75" / "blog-anxiety-ar.json"


class BlogV75Tests(unittest.TestCase):
    def test_source_is_reviewed_deep_and_cited(self):
        payload = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(payload["collection"]["status"], "reviewed")
        self.assertEqual(len(payload["articles"]), 1)
        article = payload["articles"][0]
        self.assertEqual(article["status"], "reviewed")
        visible = " ".join(p for section in article["sections"] for p in section["paragraphs"])
        self.assertGreaterEqual(len(visible.split()), 650)
        self.assertGreaterEqual(len(article["sections"]), 7)
        self.assertGreaterEqual(len(article["sources"]), 2)
        self.assertTrue(all(source["url"].startswith("https://www.who.int/") for source in article["sources"]))
        forbidden = ["يشخّصك", "أوقف الدواء", "غيّر الجرعة", "علاج مضمون", "شفاء نهائي"]
        self.assertFalse(any(token in visible for token in forbidden))

    def test_publisher_outputs_index_article_schema_and_sitemap(self):
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp)
            site.joinpath("index.html").write_text('<nav><a href="hubs/">المراكز</a></nav><div><article class="card"><h3>المراكز الموضوعية</h3></article></div>', encoding="utf-8")
            site.joinpath("sitemap.xml").write_text('<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>', encoding="utf-8")
            subprocess.run([sys.executable, str(PUBLISHER), str(site)], check=True)
            subprocess.run([sys.executable, str(FINALIZER), str(site)], check=True)
            index = site.joinpath("blog", "index.html").read_text(encoding="utf-8")
            article = site.joinpath("blog", "normal-anxiety-vs-anxiety-disorder", "index.html").read_text(encoding="utf-8")
            home = site.joinpath("index.html").read_text(encoding="utf-8")
            report = json.loads(site.joinpath("api", "blog-v75.json").read_text(encoding="utf-8"))
            self.assertIn('<html lang="ar" dir="rtl">', index)
            self.assertEqual(article.count("<h1>"), 1)
            self.assertIn('"@type": "BlogPosting"', article)
            self.assertIn('rel="canonical"', article)
            self.assertIn("منظمة الصحة العالمية", article)
            self.assertIn('href="blog/">المدونة</a>', home)
            self.assertIn("المدونة التحليلية", home)
            self.assertEqual(report["articles"], 1)
            self.assertTrue(report["reviewed"])
            root = ET.parse(site / "sitemap-blog.xml").getroot()
            self.assertEqual(root.tag.rsplit("}", 1)[-1], "urlset")
            self.assertEqual(len(list(root)), 2)


if __name__ == "__main__":
    unittest.main()
