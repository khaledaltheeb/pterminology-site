from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TRUST_PAGE = ROOT / "trust" / "index.html"
SITEMAP = ROOT / "sitemap.xml"


class TrustCenterV38Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = TRUST_PAGE.read_text(encoding="utf-8")

    def test_page_exists_and_is_arabic_rtl(self):
        self.assertTrue(TRUST_PAGE.exists())
        self.assertIn('lang="ar"', self.html)
        self.assertIn('dir="rtl"', self.html)

    def test_required_trust_topics_are_present(self):
        required = (
            "منهجية التحرير",
            "سياسة المصادر",
            "تصنيف قوة الدليل",
            "حالات المراجعة",
            "الخصوصية",
            "البيانات المحلية والحذف",
            "ملفات الارتباط",
            "سياسة التصحيح",
            "سجل التحديثات",
            "تضارب المصالح",
            "الأزمات والمساعدة العاجلة",
            "حدود الأدوات والاختبارات",
        )
        for topic in required:
            with self.subTest(topic=topic):
                self.assertIn(topic, self.html)

    def test_non_diagnostic_and_emergency_boundaries(self):
        self.assertIn("ليس للتشخيص الذاتي", self.html)
        self.assertIn("لا تثبت وجود اضطراب ولا تنفيه", self.html)
        self.assertIn("خدمات الطوارئ المحلية", self.html)
        self.assertNotIn("نضمن", self.html)
        self.assertNotIn("معتمد عالميًا", self.html)

    def test_no_unverified_named_experts_or_partners(self):
        forbidden_claims = (
            "فريق من الأطباء",
            "مراجع من استشاري",
            "شراكة مع منظمة الصحة العالمية",
            "معتمد من",
        )
        for claim in forbidden_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, self.html)

    def test_privacy_and_local_deletion_guidance(self):
        self.assertIn("الحفظ اختياريًا", self.html)
        self.assertIn("إعدادات المتصفح", self.html)
        self.assertIn("لا تكتب اسم المريض", self.html)
        self.assertIn("أي بيانات طبية أو تعريفية", self.html)

    def test_public_issue_and_external_link_disclosures(self):
        self.assertIn("بلاغات GitHub عامة", self.html)
        self.assertIn("قد تظهر في محركات البحث", self.html)
        self.assertIn("الروابط الخارجية تنقلك إلى خدمات مستقلة", self.html)
        self.assertIn("لا تتحكم المنصة في احتفاظ الطرف الثالث بالبيانات", self.html)
        self.assertRegex(
            self.html,
            r'<a href="https://github\.com/khaledaltheeb/pterminology-site/issues"[^>]*rel="external noopener"',
        )

    def test_canonical_and_structured_data(self):
        expected = "https://khaledaltheeb.github.io/pterminology-site/trust/"
        self.assertIn(f'<link rel="canonical" href="{expected}">', self.html)
        self.assertIn('type="application/ld+json"', self.html)
        self.assertIn('"@type":"WebPage"', self.html)

    def test_basic_accessibility_structure(self):
        self.assertRegex(self.html, r'<a class="skip" href="#main">')
        self.assertRegex(self.html, r'<main id="main">')
        self.assertIn('aria-label="ملخص سياسات الثقة"', self.html)
        self.assertIn('role="note"', self.html)
        self.assertNotRegex(self.html, r'<img(?![^>]*\balt=)')

    def test_sitemap_includes_trust_center(self):
        sitemap = SITEMAP.read_text(encoding="utf-8")
        self.assertIn(
            "https://khaledaltheeb.github.io/pterminology-site/trust/",
            sitemap,
        )


if __name__ == "__main__":
    unittest.main()
