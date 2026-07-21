from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "docs" / "DISABILITY_DIGNITY_SAFETY_AR.md"


class DisabilityDignitySafetyPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = POLICY.read_text(encoding="utf-8")

    def test_policy_exists_and_has_review_date(self):
        self.assertTrue(POLICY.exists())
        self.assertIn("2026-07-22", self.text)
        self.assertIn("مسودة مؤسسية", self.text)

    def test_core_dignity_and_non_stigma_requirements(self):
        required = [
            "الشخص ليس تشخيصًا",
            "نقاط القوة",
            "عبء أو مأساة",
            "تفضيل الشخص",
            "لا يقدم المحتوى تشخيصًا ذاتيًا",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_consent_assent_and_communication_are_protected(self):
        required = [
            "الموافقة والمشاركة",
            "مشاركته وقبوله العملي",
            "الامتثال الشكلي",
            "التواصل البديل والمعزز",
            "احترام الرفض",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_privacy_deletion_and_no_default_server_transfer(self):
        required = [
            "التخزين المحلي",
            "كيف يحذف",
            "عدم الإرسال إلى خادم دون موافقة موثقة",
            "قنوات بلاغ مفتوحة",
            "التنمر والاستغلال",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_behavior_must_not_be_psychologized_before_basic_causes(self):
        for phrase in (
            "الألم والمرض والدواء والبيئة والحساسية والتواصل",
            "مشكلات السمع والبصر والنوم والتواصل",
            "عند تغير السلوك أو القدرة بصورة مفاجئة",
        ):
            self.assertIn(phrase, self.text)

    def test_genetic_and_reproductive_information_is_neutral(self):
        required = [
            "المحتوى الوراثي والفحوص والخيارات الإنجابية",
            "بلغة محايدة ودقيقة",
            "حدود الاختبار",
            "قرار إنجابي بعينه",
            "قيمة حياة الشخص",
            "الاستشارة الوراثية",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_coercive_and_harmful_practices_are_rejected(self):
        required = [
            "الإكراه أو التقييد أو العقاب",
            "الحرمان من التواصل أو الحركة أو الطعام",
            "لا مجرد زيادة الامتثال",
            "كرامته، سلامته، وقدرته على التواصل",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_crisis_and_safeguarding_boundaries_exist(self):
        required = [
            "خطر وشيك",
            "اشتباه إساءة أو استغلال",
            "خدمات الطوارئ أو الحماية المحلية",
            "لا تستخدم المنصة بديلًا",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_review_status_and_corrections_are_truthful(self):
        required = [
            "حالة المراجعة",
            "لا ترفع الحالة دون دليل",
            "لا تنشأ أسماء خبراء",
            "تضارب المصالح",
            "تصحح الأخطاء الجوهرية علنًا",
        ]
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.text)

    def test_no_unverified_certification_or_guarantee_claims(self):
        forbidden_patterns = [
            r"معتمد(?:ة)? من (?:منظمة الصحة العالمية|WHO|APA|وزارة)",
            r"راجعها فريق من الخبراء",
            r"نضمن (?:الشفاء|النتيجة|التحسن)",
            r"شراكة رسمية مع",
        ]
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, self.text, flags=re.IGNORECASE))

    def test_policy_has_publish_acceptance_checklist(self):
        self.assertIn("قائمة قبول قبل النشر", self.text)
        self.assertGreaterEqual(self.text.count("هل "), 10)


if __name__ == "__main__":
    unittest.main()
