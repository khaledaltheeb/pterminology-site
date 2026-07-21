import json
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "data" / "urgent-help-governance.json"
DOC_PATH = ROOT / "docs" / "URGENT_HELP_GOVERNANCE_AR.md"


def load_policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_policy_and_document_exist():
    assert POLICY_PATH.exists()
    assert DOC_PATH.exists()


def test_review_metadata_is_explicit_and_not_falsely_approved():
    policy = load_policy()
    assert policy["review_status"] in {"draft", "needs-review", "reviewed"}
    assert policy["review_status"] != "reviewed"
    datetime.strptime(policy["reviewed_at"], "%Y-%m-%d")


def test_required_contact_fields_cover_scope_source_and_freshness():
    required = set(load_policy()["required_fields"])
    expected = {
        "entry_id",
        "country_code",
        "jurisdiction_label",
        "service_name",
        "service_type",
        "contact_method",
        "official_source_url",
        "verified_at",
        "verification_method",
        "availability_note",
        "languages",
        "audience",
        "uncertainty_note",
    }
    assert expected <= required


def test_official_source_and_reverification_are_mandatory():
    verification = load_policy()["verification"]
    assert verification["official_source_required"] is True
    assert 1 <= verification["maximum_age_days"] <= 180
    assert verification["reverify_on_material_change"] is True
    assert "search-snippet-only" in verification["prohibited_sources"]
    assert "social-post-only" in verification["prohibited_sources"]


def test_no_universal_or_unverified_emergency_claims():
    policy = load_policy()
    prohibited = " ".join(policy["prohibited_claims"])
    for phrase in [
        "هذه الجهة معتمدة من المنصة",
        "هذه الخدمة الأفضل",
        "الاتصال يضمن السلامة",
        "جميع المكالمات سرية",
        "الخدمة متاحة دائمًا",
        "تمت مراجعة الحالة بواسطة مختص",
    ]:
        assert phrase in prohibited


def test_display_rules_disclose_country_date_and_limits():
    rules = load_policy()["display_rules"]
    for key in [
        "show_country_and_scope",
        "show_verified_date",
        "show_availability_limits",
        "show_language_limits",
        "show_cost_warning_when_unknown",
    ]:
        assert rules[key] is True
    assert rules["do_not_claim_confidentiality_unless_source_confirms"] is True
    assert rules["do_not_claim_24_7_unless_source_confirms"] is True


def test_safe_fallback_does_not_invent_a_global_number():
    fallback = " ".join(load_policy()["fallback_when_local_service_unverified"])
    assert "خدمات الطوارئ المحلية" in fallback
    assert "أقرب قسم طوارئ" in fallback
    assert "لا تعتمد على الموقع" in fallback
    assert not any(char.isdigit() for char in fallback)


def test_tools_require_privacy_non_diagnosis_and_post_result_guidance():
    requirements = load_policy()["content_requirements"]
    assert requirements["non_diagnostic"] is True
    assert requirements["no_medication_instruction"] is True
    assert requirements["privacy_notice_required_if_user_input_exists"] is True
    assert requirements["post_result_guidance_required"] is True
    assert requirements["accessibility_required"] is True


def test_change_log_does_not_allow_invented_reviewer_identity():
    fields = set(load_policy()["change_log_requirements"])
    assert "reviewer_identity_if_real_and_authorized" in fields


def test_arabic_policy_covers_core_safeguards():
    text = DOC_PATH.read_text(encoding="utf-8")
    for phrase in [
        "لا تشخّص",
        "المصدر الرسمي",
        "180 يومًا",
        "الخطر الوشيك",
        "غير تشخيصي",
        "لا يمنح درجة",
        "قابلاً للاستخدام بلوحة المفاتيح",
        "لا تنشئ شبكة طوارئ عالمية",
    ]:
        assert phrase in text


def test_policy_date_is_not_in_the_future():
    reviewed_at = date.fromisoformat(load_policy()["reviewed_at"])
    assert reviewed_at <= date.today()
