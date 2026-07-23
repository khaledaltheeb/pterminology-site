import json
import tempfile
import unittest
from pathlib import Path
from subprocess import run
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v176" / "start-here-ar.json"
SCRIPT = ROOT / "scripts" / "publish_start_here_v176.py"


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.links = []
        self.text = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
    def handle_data(self, data):
        self.text.append(data)


class StartHereTests(unittest.TestCase):
    def test_source_depth_and_unique_routes(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["sections"]), 7)
        self.assertGreaterEqual(len(data["decision_steps"]), 5)
        hrefs = [item["href"] for item in data["sections"]]
        self.assertEqual(len(hrefs), len(set(hrefs)))
        self.assertTrue(all(href.startswith("/") for href in hrefs))
        self.assertGreaterEqual(len(data["description"]), 120)

    def test_build_metadata_schema_links_and_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text('<html lang="ar" dir="rtl"><main><h1>الرئيسية</h1></main></html>', encoding="utf-8")
            result = run(["python", str(SCRIPT), str(site)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            page = (site / "start-here" / "index.html").read_text(encoding="utf-8")
            parser = Collector(); parser.feed(page)
            for marker in ["canonical", "og:title", "twitter:card", "application/ld+json", "BreadcrumbList", "WebPage"]:
                self.assertIn(marker, page)
            for route in ["/encyclopedia/", "/care-guides/", "/special-needs/", "/blog/"]:
                self.assertIn(route, parser.links)
            visible = " ".join(parser.text)
            self.assertIn("لا تقدم تشخيصًا", visible)
            self.assertNotIn("شفاء مضمون", visible)
            self.assertTrue((site / "sitemap-start-here.xml").is_file())
            report = json.loads((site / "api" / "start-here-v176.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")

    def test_homepage_link_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            homepage = site / "index.html"
            homepage.write_text('<html lang="ar" dir="rtl"><main><h1>الرئيسية</h1></main></html>', encoding="utf-8")
            for _ in range(2):
                result = run(["python", str(SCRIPT), str(site)], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
            text = homepage.read_text(encoding="utf-8")
            self.assertEqual(text.count('href="start-here/"'), 1)
            self.assertEqual(text.count('id="start-here"'), 1)


if __name__ == "__main__":
    unittest.main()
