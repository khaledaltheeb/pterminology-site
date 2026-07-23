import json
import tempfile
import unittest
from pathlib import Path

from scripts.publish_anxiety_question_v181 import DATA, publish, render_page


class AnxietyQuestionV181Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))
        cls.html = render_page(cls.data)

    def test_content_is_deep_original_and_structured(self):
        text = " ".join(
            [self.data["short_answer"]]
            + [p for section in self.data["sections"] for p in section["paragraphs"]]
            + [item["answer"] for item in self.data["faq"]]
        )
        words = [word for word in text.split() if word.strip()]
        self.assertGreaterEqual(len(words), 850)
        self.assertGreaterEqual(len(self.data["sections"]), 7)
        self.assertGreaterEqual(len(self.data["faq"]), 4)
        headings = [section["heading"] for section in self.data["sections"]]
        self.assertEqual(len(headings), len(set(headings)))

    def test_sources_are_contract_ready_current_and_unique(self):
        sources = self.data["sources"]
        self.assertGreaterEqual(len(sources), 4)
        ids = [source["id"] for source in sources]
        urls = [source["url"] for source in sources]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(urls), len(set(urls)))
        required = {"id", "publisher", "title", "url", "year", "source_type", "verified_at", "claims_supported", "status"}
        for source in sources:
            self.assertFalse(required - set(source))
            self.assertTrue(source["url"].startswith("https://www.who.int/"))
            self.assertTrue(source["claims_supported"])
            self.assertEqual(source["status"], "current")
            self.assertIsInstance(source["year"], int)
            self.assertRegex(source["verified_at"], r"^\d{4}-\d{2}-\d{2}$")

    def test_safety_boundaries_are_explicit(self):
        for phrase in ["لا تشخّص", "لا تحدد علاجًا أو دواءً", "مساعدة عاجلة", "رقم الطوارئ المحلي"]:
            self.assertIn(phrase, self.html)
        for phrase in ["أنت مصاب", "تشخيص مؤكد", "توقف عن الدواء", "جرعة", "شفاء مضمون"]:
            self.assertNotIn(phrase, self.html)
        self.assertEqual(self.data["publication"]["state"], "built-not-published")
        self.assertFalse(self.data["publication"]["automatic_publication"])
        self.assertEqual(self.data["review_status"], "needs-specialist-review")

    def test_seo_schema_and_accessibility(self):
        self.assertIn('<html lang="ar" dir="rtl">', self.html)
        self.assertEqual(self.html.count("<h1>"), 1)
        self.assertIn('<link rel="canonical"', self.html)
        self.assertIn('name="description"', self.html)
        self.assertIn('property="og:title"', self.html)
        self.assertIn('name="twitter:card"', self.html)
        for schema_type in ['"@type": "WebPage"', '"@type": "FAQPage"', '"@type": "BreadcrumbList"']:
            self.assertIn(schema_type, self.html)
        self.assertIn('href="#content"', self.html)
        self.assertIn('aria-label="مسار التنقل"', self.html)

    def test_build_writes_page_sitemap_and_nonpublished_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            report = publish(site)
            page = site / report["page"]
            sitemap = site / report["sitemap"]
            api = site / "api" / "publisher-07-question-v181.json"
            self.assertTrue(page.is_file())
            self.assertTrue(sitemap.is_file())
            self.assertTrue(api.is_file())
            self.assertIn(self.data["canonical"], sitemap.read_text(encoding="utf-8"))
            self.assertEqual(report["state"], "built-not-published")
            self.assertFalse(report["live_verified"])


if __name__ == "__main__":
    unittest.main()
