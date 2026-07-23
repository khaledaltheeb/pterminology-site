import importlib.util
import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v192" / "platform-institutional-foundation-ar.json"
SCRIPT = ROOT / "scripts" / "publish_institutional_foundation_v192.py"

spec = importlib.util.spec_from_file_location("institutional_foundation_v192", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def words(self):
        return re.findall(r"[\w\u0600-\u06ff]+", " ".join(self.parts))


class InstitutionalFoundationV192Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTENT.read_text(encoding="utf-8"))

    def make_site(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        (root / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>مصطلحات علم النفس | منصة عربية للصحة النفسية</title>'
            '<meta name="description" content="وصف قديم"><meta property="og:title" content="مصطلحات علم النفس">'
            '<meta name="twitter:title" content="مصطلحات علم النفس"></head><body><header><a class="brand" href="./">مصطلحات علم النفس</a><nav><a href="encyclopedia/">الموسوعة</a></nav></header><main><h1>الرئيسية</h1></main><footer><p>قديم</p></footer></body></html>',
            encoding="utf-8",
        )
        about = root / "about" / "index.html"
        about.parent.mkdir(parents=True)
        about.write_text('<html lang="ar" dir="rtl"><head><title>عن الموقع</title></head><body><main><h1>عن الموقع</h1></main></body></html>', encoding="utf-8")
        (root / "google-test.html").write_text("google-site-verification: token", encoding="utf-8")

    def test_content_depth_honesty_and_primary_source_contract(self):
        self.assertEqual(self.data["status"], "internally-reviewed")
        self.assertEqual(self.data["risk_level"], "low")
        self.assertGreaterEqual(len(self.data["magazine"]["sections"]), 5)
        self.assertGreaterEqual(len(self.data["magazine"]["publication_checklist"]), 10)
        self.assertGreaterEqual(len(self.data["partners"]["sections"]), 4)
        self.assertIn("لا توجد", self.data["partners"]["summary"])
        sources = self.data["sources"]
        self.assertGreaterEqual(len(sources), 4)
        self.assertEqual(len({item["id"] for item in sources}), len(sources))
        self.assertEqual(len({item["url"] for item in sources}), len(sources))
        for source in sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertRegex(source["verified_at"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(source["claims_supported"])
            self.assertIn(source["source_type"], {"official_guideline", "official_health_information"})

    def test_build_metadata_schema_depth_and_footer_coverage(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            self.make_site(site)
            report = module.publish(site)
            self.assertEqual(report["status"], "built-not-published")
            self.assertEqual(report["declared_partners"], 0)
            self.assertEqual(report["declared_donors"], 0)
            self.assertEqual(report["published_research_summaries"], 0)
            self.assertEqual(report["footer_pages"], 4)
            for relative, minimum in (("magazine/index.html", 450), ("partners/index.html", 300)):
                page = (site / relative).read_text(encoding="utf-8")
                self.assertEqual(page.count("<h1>"), 1)
                for marker in ('rel="canonical"', 'name="robots"', 'property="og:title"', 'name="twitter:card"', 'application/ld+json', ':focus-visible', '@media print'):
                    self.assertIn(marker, page)
                parser = TextParser()
                parser.feed(page)
                self.assertGreaterEqual(len(parser.words), minimum)
                self.assertEqual(page.count(module.START), 1)
                self.assertEqual(page.count(module.END), 1)
            homepage = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn(self.data["platform_name"], homepage)
            self.assertIn('href="magazine/"', homepage)
            self.assertIn('href="partners/"', homepage)
            self.assertEqual(homepage.count(module.START), 1)
            self.assertEqual((site / "about/index.html").read_text(encoding="utf-8").count(module.START), 1)
            self.assertNotIn(module.START, (site / "google-test.html").read_text(encoding="utf-8"))

    def test_idempotence_sitemap_and_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            self.make_site(site)
            module.publish(site)
            first = {path.relative_to(site).as_posix(): path.read_text(encoding="utf-8") for path in site.rglob("*") if path.is_file()}
            module.publish(site)
            second = {path.relative_to(site).as_posix(): path.read_text(encoding="utf-8") for path in site.rglob("*") if path.is_file()}
            self.assertEqual(first, second)
            sitemap = (site / module.SITEMAP_NAME).read_text(encoding="utf-8")
            self.assertEqual(sitemap.count("<url>"), 2)
            self.assertEqual(sitemap.count("/magazine/"), 1)
            self.assertEqual(sitemap.count("/partners/"), 1)
            report = json.loads((site / "api/institutional-foundation-v192.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")
            self.assertNotEqual(report["status"], "published")

    def test_no_unverified_authority_or_partner_claims(self):
        text = CONTENT.read_text(encoding="utf-8")
        for forbidden in ["معتمد رسميًا", "راجعها أطباء", "شريك رسمي: منظمة", "دراسة تثبت نهائيًا", "يضمن الترتيب", "مراجعة اختصاصية خارجية مكتملة"]:
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
