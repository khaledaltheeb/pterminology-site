import json
import re
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_JSON = ROOT / "data" / "disability-dignity-safety.json"
POLICY_DOC = ROOT / "docs" / "DISABILITY_DIGNITY_SAFETY_AR.md"


class DisabilityDignitySafetyPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
        cls.text = POLICY_DOC.read_text(encoding="utf-8")

    def test_policy_files_exist_and_status_is_truthful(self):
        self.assertTrue(POLICY_JSON.is_file())
        self.assertTrue(POLICY_DOC.is_file())
        self.assertEqual(self.policy["review_status"], "needs-external-review")
        self.assertLessEqual(date.fromisoformat(self.policy["updated_at"]), date.today())
        self.assertIn("تحتاج مراجعة خارجية متخصصة", self.text)

    def test_default_is_not_blanket_authorization(self):
        self.assertFalse(self.policy["default_publishable"])
        self.assertIn("does not authorize clinical", self.policy["publication_rule"])

    def test_scope_covers_major_disability_content(self):
        scope = set(self.policy["scope"])
        for item in ["disability", "genetic-syndromes", "autism", "adhd", "communication-disorders"]:
            self.assertIn(item, scope)

    def test_core_dignity_and_non_stigma_requirements(self):
        principles = self.policy["required_principles"]
        for key in [
            "person_not_diagnosis", "respect_language_preference",
            "balance_needs_and_strengths", "non_diagnostic",
            "no_medication_instruction", "no_guaranteed_outcome",
        ]:
            self.assertTrue(principles[key])
        for phrase in ["الشخص ليس تشخيصًا", "نقاط القوة", "عبء أو مأساة", "تفضيل الشخص"]:
            self.assertIn(phrase, self.text)

    def test_consent_assent_supported_decision_and_communication(self):
        principles = self.policy["required_principles"]
        for key in [
            "consent_and_assent", "supported_decision_making",
            "respect_refusal_and_stop_signals", "aac_and_accessible_communication",
        ]:
            self.assertTrue(principles[key])
        for phrase in ["مشاركته وقبوله العملي", "اتخاذ القرار بمساندة", "التواصل البديل والمعزز", "إشارات الرفض"]:
            self.assertIn(phrase, self.text)

    def test_privacy_and_safeguarding_requirements(self):
        principles = self.policy["required_principles"]
        self.assertTrue(principles["privacy_and_data_minimization"])
        self.assertTrue(principles["safeguarding_and_abuse_awareness"])
        for phrase in ["تقليل البيانات", "كيف يحذف", "التنمر والاستغلال", "قنوات بلاغ مفتوحة"]:
            self.assertIn(phrase, self.text)

    def test_behavior_order_checks_basic_causes_before_hypothesis(self):
        order = self.policy["behavior_interpretation_order"]
        self.assertEqual(order[-1], "psychological_or_behavioral_hypothesis")
        for item in ["pain_or_illness", "medication_effects", "sleep", "communication_barriers"]:
            self.assertLess(order.index(item), order.index("psychological_or_behavioral_hypothesis"))
        self.assertIn("الألم أو المرض", self.text)
        self.assertIn("تأتي الفرضية النفسية أو السلوكية بعد", self.text)

    def test_coercive_and_exploitative_practices_are_prohibited(self):
        prohibited = set(self.policy["prohibited_practices"])
        for item in [
            "unjustified_restraint", "deprivation_of_food_or_water",
            "deprivation_of_communication", "conversion_or_cure_claims",
            "pity_or_fear_marketing",
        ]:
            self.assertIn(item, prohibited)
        for phrase in ["التقييد غير المبرر", "الحرمان من الطعام أو الماء", "لا مجرد زيادة الامتثال"]:
            self.assertIn(phrase, self.text)

    def test_media_rules_protect_consent_accessibility_and_dignity(self):
        rules = self.policy["media_rules"]
        for key in [
            "functional_alt_text", "no_crisis_or_restraint_clickbait",
            "no_unnecessary_health_disclosure", "represent_ordinary_life_and_agency",
            "specific_consent_for_identifiable_media",
        ]:
            self.assertTrue(rules[key])
        self.assertIn("نصًا بديلًا وظيفيًا", self.text)
        self.assertIn("لا تستخدم صور التقييد", self.text)

    def test_genetic_and_reproductive_information_is_neutral(self):
        rules = self.policy["genetic_content_rules"]
        for value in rules.values():
            self.assertTrue(value)
        for phrase in ["بلغة محايدة ودقيقة", "حدود الاختبار", "قرار إنجابي بعينه", "قيمة حياة الشخص"]:
            self.assertIn(phrase, self.text)

    def test_urgent_boundaries_exist(self):
        signals = set(self.policy["urgent_escalation_signals"])
        for item in ["immediate_danger", "suspected_abuse_or_exploitation", "sudden_loss_of_skills"]:
            self.assertIn(item, signals)
        for phrase in ["خطر وشيك", "اشتباه إساءة أو استغلال", "خدمات الطوارئ أو الحماية المحلية"]:
            self.assertIn(phrase, self.text)

    def test_review_and_claims_are_truthful(self):
        for phrase in [
            "لا ترفع إلى «مراجعة علميًا»", "لا تنشأ أسماء خبراء",
            "تضارب المصالح", "تصحح الأخطاء الجوهرية علنًا",
        ]:
            self.assertIn(phrase, self.text)
        forbidden_patterns = [
            r"معتمد(?:ة)? من (?:منظمة الصحة العالمية|WHO|APA|وزارة)",
            r"راجعها فريق من الخبراء",
            r"نضمن (?:الشفاء|النتيجة|التحسن)",
            r"شراكة رسمية مع",
        ]
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, self.text, flags=re.IGNORECASE))

    def test_publish_acceptance_checklist_is_complete(self):
        self.assertGreaterEqual(len(self.policy["publication_checklist"]), 10)
        self.assertIn("قائمة قبول قبل النشر", self.text)
        self.assertGreaterEqual(self.text.count("هل "), 10)


if __name__ == "__main__":
    unittest.main()
