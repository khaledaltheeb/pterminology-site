import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data" / "trust-safety-requirements.json"
DOC_PATH = ROOT / "docs" / "trust-safety-requirements-ar.md"


class TrustSafetyRequirementsV50Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.doc = DOC_PATH.read_text(encoding="utf-8")

    def test_contract_and_documentation_exist(self):
        self.assertTrue(CONTRACT_PATH.exists())
        self.assertTrue(DOC_PATH.exists())
        self.assertEqual(self.contract["contract_version"], "1.2.0")
        self.assertRegex(self.contract["reviewed_at"], r"^\d{4}-\d{2}-\d{2}$")

    def test_all_scoped_types_have_requirements(self):
        scoped_types = set(self.contract["scope"])
        requirement_types = set(self.contract["required_fields_by_type"])
        self.assertEqual(scoped_types, requirement_types)
        self.assertEqual(
            scoped_types,
            {"tool", "assessment", "course", "guide", "recovery-path"},
        )

    def test_shared_safety_fields_are_required(self):
        shared = {
            "limitations",
            "non_diagnostic_notice",
            "reviewed_at",
            "review_status",
            "safety_level",
        }
        for content_type, fields in self.contract["required_fields_by_type"].items():
            with self.subTest(content_type=content_type):
                self.assertTrue(shared.issubset(set(fields)))

    def test_professional_help_path_is_required_across_scoped_types(self):
        for content_type, fields in self.contract["required_fields_by_type"].items():
            with self.subTest(content_type=content_type):
                self.assertIn("professional_help_path", fields)

    def test_tools_and_assessments_cover_privacy_and_post_result_guidance(self):
        tools = set(self.contract["required_fields_by_type"]["tool"])
        assessments = set(self.contract["required_fields_by_type"]["assessment"])
        lifecycle_fields = {
            "privacy_notice",
            "storage_behavior",
            "retention_period",
            "consent_withdrawal",
            "deletion_method",
            "deletion_confirmation",
            "post_result_guidance",
            "professional_help_path",
        }
        self.assertTrue(
            lifecycle_fields.union({"input_validation", "calculation_method"}).issubset(tools)
        )
        self.assertTrue(
            lifecycle_fields.union(
                {
                    "scoring_method",
                    "score_boundaries",
                    "result_interpretation_limits",
                }
            ).issubset(assessments)
        )

    def test_recovery_paths_require_escalation_and_emergency_guidance(self):
        recovery = set(self.contract["required_fields_by_type"]["recovery-path"])
        self.assertIn("escalation_criteria", recovery)
        self.assertIn("professional_help_path", recovery)
        self.assertIn("emergency_path", recovery)

    def test_safety_levels_are_complete_and_proportionate(self):
        levels = self.contract["safety_levels"]
        self.assertEqual(set(levels), {"general", "sensitive", "urgent"})

        self.assertFalse(levels["general"]["requires_professional_help_path"])
        self.assertFalse(levels["general"]["requires_emergency_path"])

        self.assertTrue(levels["sensitive"]["requires_professional_help_path"])
        self.assertFalse(levels["sensitive"]["requires_emergency_path"])

        self.assertTrue(levels["urgent"]["requires_professional_help_path"])
        self.assertTrue(levels["urgent"]["requires_emergency_path"])

    def test_privacy_defaults_are_protective(self):
        privacy = self.contract["privacy_requirements"]
        self.assertFalse(privacy["default_server_transmission"])
        self.assertTrue(privacy["local_storage_requires_explicit_opt_in"])
        self.assertTrue(privacy["consent_must_be_withdrawable"])
        self.assertTrue(privacy["must_state_retention_period_or_session_scope"])
        self.assertTrue(privacy["must_explain_complete_deletion"])
        self.assertTrue(privacy["must_confirm_deletion_result"])
        self.assertTrue(privacy["must_warn_against_identifying_free_text"])
        self.assertTrue(privacy["non_essential_cookies_require_prior_consent"])
        self.assertTrue(privacy["analytics_must_not_receive_sensitive_tool_entries"])

    def test_data_lifecycle_prevents_silent_or_partial_deletion(self):
        lifecycle = self.contract["data_lifecycle_requirements"]
        self.assertTrue(lifecycle["retention_must_be_specific"])
        self.assertTrue(
            lifecycle["indefinite_retention_is_forbidden_without_documented_necessity"]
        )
        self.assertTrue(lifecycle["withdrawal_must_stop_future_optional_storage"])
        self.assertTrue(lifecycle["withdrawal_must_not_silently_delete_without_warning"])
        self.assertTrue(lifecycle["delete_all_must_cover_all_local_keys_owned_by_the_tool"])
        self.assertTrue(lifecycle["deletion_must_be_idempotent"])
        self.assertTrue(lifecycle["deletion_failure_must_be_reported_accessibly"])

    def test_result_boundaries_prevent_diagnosis_and_over_escalation(self):
        safety = self.contract["result_safety_requirements"]
        self.assertTrue(safety["must_state_not_diagnostic"])
        self.assertTrue(safety["must_not_claim_to_confirm_or_exclude_a_disorder"])
        self.assertTrue(safety["must_explain_next_step"])
        self.assertTrue(safety["must_distinguish_education_from_professional_care"])
        self.assertTrue(safety["sensitive_results_require_professional_help_guidance"])
        self.assertTrue(safety["emergency_guidance_requires_urgent_level_or_explicit_escalation"])
        self.assertTrue(safety["urgent_results_require_local_emergency_guidance"])

    def test_forbidden_claims_cover_diagnosis_and_unverified_authority(self):
        claims = "\n".join(self.contract["forbidden_claims"])
        for phrase in (
            "نضمن التشخيص",
            "يؤكد وجود الاضطراب",
            "ينفي وجود الاضطراب",
            "بديل عن الطبيب",
            "معتمد عالميًا",
            "شراكة مع منظمة الصحة العالمية",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, claims)

    def test_evidence_labels_include_uncertainty(self):
        labels = set(self.contract["evidence_labels"])
        self.assertIn("إرشاد رسمي", labels)
        self.assertIn("مراجعة منهجية", labels)
        self.assertIn("دليل غير كافٍ", labels)
        self.assertIn("خبرة عملية غير محسومة", labels)

    def test_change_control_requires_verification(self):
        controls = self.contract["change_control"]
        self.assertTrue(controls["material_changes_require_log_entry"])
        self.assertTrue(controls["medical_or_psychological_claim_changes_require_source_review"])
        self.assertTrue(controls["named_experts_require_documented_identity_and_role"])
        self.assertTrue(controls["partnership_claims_require_public_verification"])

    def test_arabic_documentation_explains_limits_and_data_lifecycle(self):
        required_phrases = (
            "ليست تشخيصًا ذاتيًا",
            "التخزين المحلي يجب أن يكون اختياريًا",
            "مدة الاحتفاظ",
            "سحب الموافقة",
            "زر الحذف الشامل",
            "ملفات الارتباط غير الضرورية لا تُفعّل قبل موافقة صريحة",
            "لا يجوز إرسال مدخلات الأدوات النفسية الحساسة إلى التحليلات",
            "لا يجوز للنتيجة أن تؤكد اضطرابًا أو تنفيه",
            "المساعدة المهنية غير العاجلة والطوارئ",
            "لا يفرض مسار طوارئ افتراضيًا",
            "لا يجوز ذكر خبير أو مراجع أو شريك أو اعتماد",
            "لا يغني نجاح الاختبار عن مراجعة المحتوى نفسه",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.doc)


if __name__ == "__main__":
    unittest.main()
