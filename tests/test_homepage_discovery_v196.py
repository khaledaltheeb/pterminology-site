import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
SCRIPT = ROOT / "scripts" / "apply_homepage_v20.py"

spec = importlib.util.spec_from_file_location("homepage_v196", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class AnchorCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_data(self, data):
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._parts).split())))
            self._href = None
            self._parts = []


class HomepageDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = INDEX.read_text(encoding="utf-8")
        cls.parser = AnchorCollector()
        cls.parser.feed(cls.text)

    def test_metadata_and_heading_depth(self):
        self.assertEqual(self.text.count("<h1>"), 1)
        self.assertGreaterEqual(len(re.findall(r"<h2\b", self.text)), 4)
        self.assertGreaterEqual(len(re.findall(r"<h3\b", self.text)), 10)
        title = re.search(r"<title>(.*?)</title>", self.text, re.S).group(1)
        description = re.search(r'<meta name="description" content="([^"]+)"', self.text).group(1)
        self.assertIn("موسوعة", title)
        self.assertIn("أدلة", title)
        self.assertGreaterEqual(len(description), 120)
        self.assertLessEqual(len(description), 180)
        self.assertIn("بلوج", description)
        self.assertIn("ذوي الاحتياجات", description)

    def test_core_routes_are_visible_and_descriptive(self):
        hrefs = [href for href, _ in self.parser.links]
        labels = [label for _, label in self.parser.links]
        for route in module.DISCOVERY_ROUTES:
            self.assertIn(route, hrefs)
        for generic in ["اضغط هنا", "اقرأ المزيد", "المزيد"]:
            self.assertNotIn(generic, labels)
        discovery_labels = [label for href, label in self.parser.links if href in module.DISCOVERY_ROUTES]
        self.assertGreaterEqual(len(set(discovery_labels)), 11)
        self.assertEqual(self.text.count('href="special-needs/"'), 2)
        self.assertEqual(self.text.count("data-special-needs-v73"), 1)

    def test_structured_navigation_matches_visible_routes(self):
        raw = re.search(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', self.text, re.S).group(1)
        graph = json.loads(raw)["@graph"]
        item_list = next(item for item in graph if item.get("@type") == "ItemList")
        self.assertEqual(item_list["numberOfItems"], len(module.DISCOVERY_ROUTES))
        schema_urls = [item["url"] for item in item_list["itemListElement"]]
        self.assertEqual(len(schema_urls), len(set(schema_urls)))
        for route in module.DISCOVERY_ROUTES:
            self.assertIn(f"https://khaledaltheeb.github.io/pterminology-site/{route}", schema_urls)

    def test_build_report_and_copy_are_truthful(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            with patch.object(module, "SITE", site), patch.object(module, "TARGET", site / "index.html"), patch.object(module, "run_publisher"), patch.object(module, "synchronize_care_guides_report"), patch.object(module, "register_sitemap"):
                module.main()
            self.assertEqual((site / "index.html").read_text(encoding="utf-8"), self.text)
            report = json.loads((site / "api" / "homepage-v20.json").read_text(encoding="utf-8"))
            discovery = json.loads((site / "api" / "homepage-discovery-v196.json").read_text(encoding="utf-8"))
            self.assertEqual(report["discovery_version"], 196)
            self.assertEqual(report["discovery_route_count"], 11)
            self.assertTrue(report["blog_linked"])
            self.assertTrue(report["special_needs_linked"])
            self.assertEqual(report["health_publication_gate"], 192)
            self.assertEqual(discovery["status"], "built-not-published")
            self.assertEqual(discovery["route_count"], 11)

    def test_accessibility_and_visual_regression_guards(self):
        for marker in ['class="skip" href="#main"', ':focus-visible', '@media(prefers-reduced-motion:reduce)', 'aria-label="التنقل الرئيسي"', 'aria-label="روابط مؤسسية"']:
            self.assertIn(marker, self.text)
        for forbidden in ["background:#071827", "background:#000", "background:black"]:
            self.assertNotIn(forbidden, self.text)


if __name__ == "__main__":
    unittest.main()
