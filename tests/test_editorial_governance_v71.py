import json
import re
import unittest
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data" / "editorial-governance.json"
DOC_PATH = ROOT / "docs" / "EDITORIAL_GOVERNANCE_AR.md"


class EditorialGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.text = DOC_PATH.read_text(encoding="utf-8")

    def test_files_status_and_date_are_truthful(self):
        self.assertTrue(POLICY_PATH.is_file())
        self.assertTrue(DOC_PATH.is_file())
        self.assertEqual(self.policy["review_status"], "institutional-draft")
        self.assertFalse(self.policy["default_publishable"])
        self.assertLessEqual(date.fromisoformat(self.policy["updated_at"]), date.today())
        self.assertIn("مسودة مؤسسية قابلة للاختبار", self.text)

    def test_content_review_and_safety_vocabularies_are_bounded(self):
        self.assertGreaterEqual(len(self.policy["content_types"]), 8)
        self.assertEqual(
            set(self.policy["safety_levels"]), {"general", "sensitive", "urgent"}
        )
        self.assertIn("withdrawn", self.policy["review_statuses"])
        self.assertIn("correction-required", self.policy["review_statuses"])

    def test_evidence_hierarchy_and_prohibited_sources_are_explicit(self):
        tiers = self.policy["evidence_tiers"]
        self.assertIn("official_guideline", tiers["tier_1"])
        self.assertIn("systematic_review_or_meta_analysis", tiers["tier_1"])
        for item in [
            "ai_generated_answer", "search_snippet", "unsourced_social_post",
            "affiliate_page", "anonymous_blog",
        ]:
            self.assertIn(item, tiers["prohibited_as_evidence"])
        self.assertIn("ليس مصدرًا علميًا", self.text)

    def test_required_fields_cover_review_sources_corrections_and_conflicts(self):
        required = set(self.policy["required_fields"])
        for item in [
            "safety_level", "review_status", "reviewed_at", "review_due_at",
            "sources", "correction_history", "conflict_of_interest",
        ]:
            self.assertIn(item, required)

    def test_review_intervals_are_stricter_with_risk(self):
        intervals = self.policy["review_intervals_days"]
        self.assertEqual(intervals["general"], 365)
        self.assertEqual(intervals["sensitive"], 180)
        self.assertEqual(intervals["urgent"], 90)
        self.assertGreater(intervals["general"], intervals["sensitive"])
        self.assertGreater(intervals["sensitive"], intervals["urgent"])

    def test_source_rules_prevent_citation_theater(self):
        rules = self.policy["source_rules"]
        for key in [
            "sensitive_requires_tier_1", "urgent_requires_current_official_source",
            "single_study_cannot_support_general_recommendation",
            "source_must_support_the_specific_claim", "citation_dumping_is_prohibited",
            "ai_may_assist_workflow_but_is_not_a_source",
            "rights_and_license_must_be_recorded_for_instruments",
        ]:
            self.assertTrue(rules[key])
        self.assertIn("يمنع حشد مراجع", self.text)

    def test_review_claims_require_real_verified_evidence(self):
        rules = self.policy["review_rules"]
        for value in rules.values():
            self.assertTrue(value)
        self.assertIn("لا ترفع حالة المراجعة دون دليل", self.text)
        self.assertIn("مراجعة خارجية فعلية موثقة", self.text)

    def test_corrections_and_withdrawal_are_required(self):
        rules = self.policy["correction_rules"]
        for value in rules.values():
            self.assertTrue(value)
        for phrase in [
            "قناة واضحة للإبلاغ عن خطأ", "يسجل التصحيح الجوهري",
            "يسحب المحتوى الضار", "أثر تدقيقي داخلي",
        ]:
            self.assertIn(phrase, self.text)

    def test_conflicts_and_sponsorship_are_disclosed(self):
        rules = self.policy["conflict_rules"]
        for value in rules.values():
            self.assertTrue(value)
        self.assertIn("لا يسمح للجهة الراعية بالتحكم", self.text)
        self.assertIn("لا يتحول رابط أفلييت إلى دليل", self.text)

    def test_no_false_external_review_or_certification_claims(self):
        forbidden = [
            r"معتمد(?:ة)? من (?:منظمة الصحة العالمية|WHO|APA|وزارة)",
            r"راجعها فريق من الخبراء",
            r"شراكة رسمية مع",
            r"نضمن (?:الشفاء|النتيجة|التحسن)",
        ]
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, self.text, flags=re.IGNORECASE))

    def test_publish_checklist_is_actionable(self):
        self.assertIn("قائمة قبول قبل النشر", self.text)
        self.assertGreaterEqual(self.text.count("هل "), 10)
        self.assertIn("AI output", self.policy["publication_rule"])


if __name__ == "__main__":
    unittest.main()
