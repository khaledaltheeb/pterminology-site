import importlib.util
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"
PUBLISHER = ROOT / "scripts" / "publish_institutional_foundation_v192.py"

apply_spec = importlib.util.spec_from_file_location("apply_homepage_v20", APPLY)
apply_module = importlib.util.module_from_spec(apply_spec)
assert apply_spec.loader is not None
apply_spec.loader.exec_module(apply_module)

publisher_spec = importlib.util.spec_from_file_location("institutional_foundation_v192", PUBLISHER)
publisher_module = importlib.util.module_from_spec(publisher_spec)
assert publisher_spec.loader is not None
publisher_spec.loader.exec_module(publisher_module)


class InstitutionalProductionV194Tests(unittest.TestCase):
    def make_site(self, site: Path) -> None:
        site.mkdir(parents=True, exist_ok=True)
        (site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>مصطلحات علم النفس | منصة عربية للصحة النفسية</title>'
            '<meta name="description" content="وصف"><meta property="og:title" content="مصطلحات علم النفس">'
            '<meta name="twitter:title" content="مصطلحات علم النفس"></head><body><header><a class="brand" href="./">مصطلحات علم النفس</a>'
            '<nav><a href="encyclopedia/">الموسوعة</a></nav></header><main><h1>الرئيسية</h1></main><footer>قديم</footer></body></html>',
            encoding="utf-8",
        )
        page = site / "about" / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text('<html lang="ar" dir="rtl"><head><title>عن الموقع</title></head><body><main><h1>عن الموقع</h1></main></body></html>', encoding="utf-8")
        (site / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
            encoding="utf-8",
        )

    def test_pipeline_invokes_after_health_gate_and_registers_once(self):
        text = APPLY.read_text(encoding="utf-8")
        health = 'run_publisher("enforce_health_publication_gate_v192.py")'
        publisher = 'run_publisher("publish_institutional_foundation_v192.py")'
        sitemap = 'register_sitemap("sitemap-institutional-foundation.xml")'
        self.assertEqual(text.count(publisher), 1)
        self.assertEqual(text.count(sitemap), 1)
        self.assertLess(text.index(health), text.index(publisher))
        self.assertLess(text.index(publisher), text.index(sitemap))
        self.assertIn('"institutional_foundation_publisher": 192', text)
        self.assertIn('"institutional_foundation_sitemap_sync": 194', text)

    def test_isolated_production_registration_is_idempotent_and_not_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            self.make_site(site)
            report = publisher_module.publish(site)
            self.assertEqual(report["status"], "built-not-published")
            self.assertEqual(report["declared_partners"], 0)
            self.assertEqual(report["published_research_summaries"], 0)
            old_site = apply_module.SITE
            try:
                apply_module.SITE = site
                apply_module.register_sitemap(publisher_module.SITEMAP_NAME)
                apply_module.register_sitemap(publisher_module.SITEMAP_NAME)
            finally:
                apply_module.SITE = old_site
            root = ET.parse(site / "sitemap.xml").getroot()
            targets = [(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")]
            expected = "https://khaledaltheeb.github.io/pterminology-site/sitemap-institutional-foundation.xml"
            self.assertEqual(targets.count(expected), 1)
            self.assertTrue((site / "magazine" / "index.html").is_file())
            self.assertTrue((site / "partners" / "index.html").is_file())
            homepage = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn("المنصة الشاملة للصحة النفسية", homepage)
            self.assertEqual(homepage.count(publisher_module.START), 1)
            api = json.loads((site / "api" / "institutional-foundation-v192.json").read_text(encoding="utf-8"))
            self.assertEqual(api["status"], "built-not-published")
            self.assertNotEqual(api["status"], "published")

    def test_pages_have_discovery_metadata_and_honest_empty_relationship_register(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary) / "site"
            self.make_site(site)
            publisher_module.publish(site)
            magazine = (site / "magazine" / "index.html").read_text(encoding="utf-8")
            partners = (site / "partners" / "index.html").read_text(encoding="utf-8")
            for page in (magazine, partners):
                self.assertEqual(page.count("<h1>"), 1)
                self.assertIn('rel="canonical"', page)
                self.assertIn('name="robots" content="index,follow', page)
                self.assertIn('property="og:title"', page)
                self.assertIn('name="twitter:card"', page)
                self.assertIn('application/ld+json', page)
                self.assertIn('@media print', page)
                self.assertIn(':focus-visible', page)
            self.assertIn("لم تُنشر في هذه الحزمة ملخصات دراسات منفردة بعد", magazine)
            self.assertIn("المانحون المعلنون:</strong> لا يوجد", partners)
            self.assertIn("الشركاء الرسميون المعلنون:</strong> لا يوجد", partners)
            for forbidden in ["شريك رسمي: منظمة الصحة العالمية", "مراجعة طبية خارجية مكتملة", "منشور حيًا", "published\"", "معتمد رسميًا"]:
                self.assertNotIn(forbidden, magazine + partners)


if __name__ == "__main__":
    unittest.main()
