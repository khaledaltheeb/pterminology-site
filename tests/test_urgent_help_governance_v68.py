import json
import unittest
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data" / "urgent-help-governance.json"
DOC_PATH = ROOT / "docs" / "URGENT_HELP_GOVERNANCE_AR.md"


class UrgentHelpGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.services = cls.policy["services"]

    def test_policy_and_document_exist(self):
        self.assertTrue(POLICY_PATH.is_file())
        self.assertTrue(DOC_PATH.is_file())

    def test_default_deny_and_empty_registry_authorize_nothing(self):
        self.assertFalse(self.policy["default_publishable"])
        if not self.services:
            self.assertIn("authorizes no phone number", self.policy["publication_rule"])

    def test_review_metadata_is_explicit_without_false_external_approval(self):
        self.assertEqual(self.policy["review_status"], "needs-external-review")
        updated_at = date.fromisoformat(self.policy["updated_at"])
        self.assertLessEqual(updated_at, date.today())

    def test_required_fields_cover_scope_source_freshness_and_disclosure(self):
        required = set(self.policy["required_fields"])
        expected = {
            "entry_id", "status", "country_code", "jurisdiction_label",
            "service_name", "service_type", "contact_method",
            "official_source_url", "source_authority_type", "verified_at",
            "review_due_at", "verification_method", "availability_note",
            "languages", "audience", "cost_note", "confidentiality_note",
            "uncertainty_note", "allowed_surfaces",
        }
        self.assertTrue(expected <= required)

    def test_official_source_and_freshness_are_mandatory(self):
        verification = self.policy["verification"]
        self.assertTrue(verification["official_source_required"])
        self.assertLessEqual(verification["maximum_age_days"], 90)
        self.assertTrue(verification["reverify_on_material_change"])
        self.assertTrue(verification["require_second_check_for_contact_changes"])
        for source in ["search-snippet-only", "social-post-only", "ai-generated-answer"]:
            self.assertIn(source, verification["prohibited_sources"])

    def test_services_have_unique_ids_and_allowed_statuses(self):
        ids = [item.get("entry_id") for item in self.services]
        self.assertEqual(len(ids), len(set(ids)))
        allowed = set(self.policy["allowed_statuses"])
        for item in self.services:
            self.assertIn(item.get("status"), allowed)

    def test_verified_services_satisfy_publication_contract(self):
        required = set(self.policy["required_fields"])
        allowed_services = set(self.policy["allowed_service_types"])
        allowed_contacts = set(self.policy["allowed_contact_types"])
        max_age = int(self.policy["verification"]["maximum_age_days"])
        for item in self.services:
            if item.get("status") != "verified":
                self.assertFalse(item.get("publishable", False))
                continue
            self.assertFalse(required - set(item), f"missing fields for {item.get('entry_id')}")
            self.assertIn(item["service_type"], allowed_services)
            self.assertIn(item["contact_method"]["type"], allowed_contacts)
            parsed = urlparse(item["official_source_url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.netloc)
            verified_at = datetime.strptime(item["verified_at"], "%Y-%m-%d").date()
            review_due = datetime.strptime(item["review_due_at"], "%Y-%m-%d").date()
            self.assertGreater(review_due, verified_at)
            self.assertLessEqual((review_due - verified_at).days, max_age)
            self.assertGreaterEqual(review_due, date.today())

    def test_display_rules_expose_scope_dates_and_limits(self):
        rules = self.policy["display_rules"]
        required_true = [
            "show_country_and_scope", "show_verified_date", "show_review_due_date",
            "show_availability_limits", "show_language_limits", "show_cost_note",
            "show_confidentiality_note", "show_uncertainty_note",
            "do_not_claim_confidentiality_unless_source_confirms",
            "do_not_claim_24_7_unless_source_confirms",
            "do_not_claim_free_service_unless_source_confirms",
        ]
        for key in required_true:
            self.assertTrue(rules[key])

    def test_safe_fallback_invents_no_global_number(self):
        fallback = " ".join(self.policy["fallback_when_local_service_unverified"])
        self.assertIn("خدمات الطوارئ المحلية", fallback)
        self.assertIn("أقرب قسم طوارئ", fallback)
        self.assertIn("لا تعتمد على الموقع", fallback)
        self.assertFalse(any(char.isdigit() for char in fallback))

    def test_crisis_content_does_not_score_or_delay_help(self):
        contract = self.policy["crisis_content_contract"]
        for key in [
            "immediate_action_before_explanation", "no_clinical_risk_score",
            "no_diagnostic_label", "no_medication_instruction",
            "no_guaranteed_outcome", "no_mandatory_account_or_form_before_help",
            "keyboard_and_screen_reader_access", "mobile_access",
            "privacy_notice_if_user_input_exists", "post_result_guidance",
        ]:
            self.assertTrue(contract[key])

    def test_prohibited_claims_cover_core_misrepresentations(self):
        claims = " ".join(self.policy["prohibited_claims"])
        for phrase in [
            "هذه الجهة معتمدة من المنصة", "هذه الخدمة الأفضل",
            "الاتصال يضمن السلامة", "جميع المكالمات سرية",
            "الخدمة متاحة دائمًا", "الخدمة مجانية للجميع",
            "تمت مراجعة حالتك بواسطة مختص", "هذا الرقم يعمل في جميع البلدان",
        ]:
            self.assertIn(phrase, claims)

    def test_arabic_policy_covers_core_safeguards(self):
        text = DOC_PATH.read_text(encoding="utf-8")
        for phrase in [
            "ممنوعة من النشر افتراضيًا", "المصدر الرسمي", "90 يومًا",
            "الخطر الوشيك", "لا تنتج درجة خطر سريرية",
            "لا يخترع الموقع رقمًا عالميًا", "قابلة للاستخدام بلوحة المفاتيح",
            "لا تنشئ شبكة طوارئ عالمية",
        ]:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
