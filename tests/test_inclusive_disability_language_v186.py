import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v186" / "inclusive-disability-language-ar.json"
SCRIPT = ROOT / "scripts" / "publish_inclusive_disability_language_v186.py"

spec = importlib.util.spec_from_file_location("inclusive_language_v186", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class InclusiveDisabilityLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CONTENT.read_text(encoding="utf-8"))

    def test_content_depth_and_nonclinical_boundaries(self):
        self.assertEqual(self.data["status"], "internally-reviewed")
        self.assertGreaterEqual(len(self.data["principles"]), 6)
        self.assertGreaterEqual(len(self.data["replace_examples"]), 8)
        self.assertGreaterEqual(len(self.data["context_checklist"]), 8)
        self.assertGreaterEqual(len(self.data["contexts"]), 4)
        limits = self.data["professional_limits"]
        for marker in ["ليس", "تشخيص", "تفضيل الشخص"]:
            self.assertIn(marker, limits)

    def test_language_avoids_pity_and_forced_euphemisms(self):
        text = json.dumps(self.data, ensure_ascii=False)
        for marker in ["الشفقة", "البطولة", "من ذوي الهمم", "يستخدم كرسيًا متحركًا", "الموافقة"]:
            self.assertIn(marker, text)
        self.assertNotIn("الأبطال الخارقون", text)
        self.assertNotIn("رغم معاناته انتصر", text)

    def test_sources_are_official_unique_and_traceable(self):
        sources = self.data["sources"]
        self.assertGreaterEqual(len(sources), 3)
        urls = [item["url"] for item in sources]
        self.assertEqual(len(urls), len(set(urls)))
        for source in sources:
            self.assertTrue(source["url"].startswith("https://"))
            self.assertIn(source["publisher"], {"United Nations", "World Health Organization", "OHCHR"})
            self.assertRegex(source["verified_at"], r"^20\d{2}-\d{2}-\d{2}$")
            self.assertTrue(source["supports"])

    def test_build_has_seo_schema_rtl_and_contextual_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            for relative, title in [
                ("special-needs/index.html", "ذوو الاحتياجات"),
                ("audiences/family/index.html", "الأسرة"),
                ("audiences/teacher/index.html", "المعلم"),
            ]:
                path = site / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'<html lang="ar" dir="rtl"><main><h1>{title}</h1></main></html>', encoding="utf-8")
            output = module.publish(site)
            html = output.read_text(encoding="utf-8")
            self.assertIn('<html lang="ar" dir="rtl">', html)
            self.assertEqual(html.count("<h1>"), 1)
            self.assertIn('<link rel="canonical"', html)
            self.assertIn('"@type": "Article"', html)
            self.assertIn('"@type": "BreadcrumbList"', html)
            self.assertIn('property="og:title"', html)
            self.assertIn("citation", html)
            href = "/special-needs/inclusive-language-disability/"
            for relative in ["special-needs/index.html", "audiences/family/index.html", "audiences/teacher/index.html"]:
                self.assertIn(href, (site / relative).read_text(encoding="utf-8"))

    def test_build_is_idempotent_and_not_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            hub = site / "special-needs" / "index.html"
            hub.parent.mkdir(parents=True)
            hub.write_text('<html lang="ar" dir="rtl"><main></main></html>', encoding="utf-8")
            module.publish(site)
            first = hub.read_text(encoding="utf-8")
            module.publish(site)
            second = hub.read_text(encoding="utf-8")
            self.assertEqual(first, second)
            report = json.loads((site / "api" / "inclusive-disability-language-v186.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "built-not-published")
            self.assertNotEqual(report["status"], "published")


if __name__ == "__main__":
    unittest.main()
