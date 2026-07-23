import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_blog_hub_v196.py"

spec = importlib.util.spec_from_file_location("blog_hub_v196", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class BlogHubV196Tests(unittest.TestCase):
    def test_rendered_hub_has_metadata_schema_depth_and_real_paths(self):
        text = module.render()
        self.assertEqual(text.count("<h1>"), 1)
        self.assertGreaterEqual(text.count("<h2"), 9)
        for marker in [
            'rel="canonical"',
            'name="description"',
            'property="og:title"',
            'name="twitter:card"',
            '"@type": "CollectionPage"',
            '"@type": "BreadcrumbList"',
            '"@type": "ItemList"',
            'class="skip" href="#content"',
            ':focus-visible',
            '@media(prefers-reduced-motion:reduce)',
            "ليس تشخيصًا",
        ]:
            self.assertIn(marker, text)
        for item in module.ROUTES:
            self.assertIn(f'{module.PREFIX}{item["href"]}', text)
        for generic in [">اضغط هنا<", ">اقرأ المزيد<", ">المزيد<"]:
            self.assertNotIn(generic, text)

    def test_publish_writes_page_report_and_single_url_sitemap(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            report = module.publish(site)
            page = site / "blog" / "index.html"
            sitemap = site / "sitemap-blog.xml"
            api = site / "api" / "blog-hub-v196.json"
            self.assertTrue(page.is_file())
            self.assertTrue(sitemap.is_file())
            self.assertTrue(api.is_file())
            self.assertEqual(report["status"], "built-not-published")
            self.assertEqual(report["pathways"], len(module.ROUTES))
            stored = json.loads(api.read_text(encoding="utf-8"))
            self.assertEqual(stored, report)
            root = ET.parse(sitemap).getroot()
            urls = [(node.text or "").strip() for node in root.findall("{*}url/{*}loc")]
            self.assertEqual(urls, [module.canonical()])


if __name__ == "__main__":
    unittest.main()
