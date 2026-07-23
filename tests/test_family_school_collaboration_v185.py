import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v185" / "family-school-collaboration-ar.json"
SCRIPT = ROOT / "scripts" / "publish_family_school_collaboration_v185.py"


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []
        self.h1 = 0

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag == "h1":
            self.h1 += 1

    def handle_data(self, data):
        self.text.append(data)


class FamilySchoolCollaborationTests(unittest.TestCase):
    def test_source_depth_safety_and_evidence(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "internally-reviewed")
        self.assertGreaterEqual(len(data["principles"]), 5)
        self.assertGreaterEqual(len(data["meeting_steps"]), 7)
        self.assertGreaterEqual(len(data["do_not_do"]), 5)
        self.assertGreaterEqual(len(data["sources"]), 3)
        self.assertEqual(len({s["source_id"] for s in data["sources"]}), len(data["sources"]))
        self.assertTrue(all(s["url"].startswith("https://") for s in data["sources"]))
        joined = json.dumps(data, ensure_ascii=False)
        for phrase in ["لا يشخّص", "صوت الطالب", "الخصوصية", "الحاجز"]:
            self.assertIn(phrase, joined)
        for phrase in ["شفاء مضمون", "غيّر الدواء", "أوقف الدواء"]:
            self.assertNotIn(phrase, joined)

    def build(self, site: Path):
        (site / "special-needs").mkdir(parents=True)
        (site / "audiences" / "family").mkdir(parents=True)
        (site / "audiences" / "teacher").mkdir(parents=True)
        for path, title in [
            (site / "special-needs" / "index.html", "ذوو الاحتياجات"),
            (site / "audiences" / "family" / "index.html", "الأسرة"),
            (site / "audiences" / "teacher" / "index.html", "المعلم"),
        ]:
            path.write_text(f'<html lang="ar" dir="rtl"><main><h1>{title}</h1></main></html>', encoding="utf-8")
        (site / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>', encoding="utf-8")
        result = run(["python", str(SCRIPT), str(site)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_build_metadata_links_print_and_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self.build(site)
            guide = site / "special-needs" / "family-school-collaboration-inclusive-support" / "index.html"
            worksheet = site / "resources" / "worksheets" / "family-school-collaboration" / "index.html"
            self.assertTrue(guide.is_file())
            self.assertTrue(worksheet.is_file())
            for page in [guide, worksheet]:
                text = page.read_text(encoding="utf-8")
                parser = Collector(); parser.feed(text)
                self.assertEqual(parser.h1, 1)
                for marker in ["canonical", "application/ld+json", "BreadcrumbList", 'lang="ar"', 'dir="rtl"']:
                    self.assertIn(marker, text)
                self.assertIn("لا", " ".join(parser.text))
            self.assertIn("window.print()", worksheet.read_text(encoding="utf-8"))
            report = json.loads((site / "api" / "family-school-collaboration-v185.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")
            self.assertEqual(len(report["generated_pages"]), 2)
            self.assertEqual(report["sitemap_urls"], 2)

    def test_linking_and_sitemap_are_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            self.build(site)
            self.build(site)
            for path in [site / "special-needs" / "index.html", site / "audiences" / "family" / "index.html", site / "audiences" / "teacher" / "index.html"]:
                self.assertEqual(path.read_text(encoding="utf-8").count("data-family-school-v185"), 1)
            sitemap = (site / "sitemap.xml").read_text(encoding="utf-8")
            self.assertEqual(sitemap.count("sitemap-family-school-collaboration.xml"), 1)


if __name__ == "__main__":
    unittest.main()
