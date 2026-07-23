import sys
import unittest
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.access import (  # noqa: E402
    CaseAccessContext,
    InstitutionAuthorization,
    ProviderCredential,
    evaluate_assessment_access,
)


APPROVED_ENTRY = {
    "id": "synthetic-functional-protocol",
    "enabled": True,
    "enablement_blockers": [],
    "license_status": "platform_authored_approved",
    "digital_right_status": "allowed",
    "qualified_roles": ["occupational_therapist"],
    "required_training_ids": ["functional-protocol-v1"],
    "languages": ["ar", "en"],
    "age_min_months": 36,
    "age_max_months": 216,
    "approved_country_codes": ["JO"],
}


def provider(**overrides):
    values = {
        "provider_id": "PROV-1",
        "institution_id": "INST-1",
        "roles": frozenset({"occupational_therapist"}),
        "active": True,
        "professional_license_expires": date(2027, 1, 1),
        "authorized_tool_ids": frozenset({"synthetic-functional-protocol"}),
        "completed_training_ids": frozenset({"functional-protocol-v1"}),
        "languages": frozenset({"ar"}),
    }
    values.update(overrides)
    return ProviderCredential(**values)


def institution(**overrides):
    values = {
        "institution_id": "INST-1",
        "active": True,
        "approved_tool_ids": frozenset({"synthetic-functional-protocol"}),
        "data_processing_agreement_active": True,
        "clinical_governance_active": True,
    }
    values.update(overrides)
    return InstitutionAuthorization(**values)


def case(**overrides):
    values = {
        "case_id": "CASE-TEST-0001",
        "institution_id": "INST-1",
        "age_months": 120,
        "assessment_language": "ar",
        "country_code": "JO",
        "approved_plan_tool_ids": frozenset({"synthetic-functional-protocol"}),
        "consent_scopes": frozenset({"assessment"}),
        "safety_level": "none_identified",
    }
    values.update(overrides)
    return CaseAccessContext(**values)


class AssessmentAccessTests(unittest.TestCase):
    def test_fully_authorized_request_is_allowed(self) -> None:
        decision = evaluate_assessment_access(
            catalog_entry=APPROVED_ENTRY,
            provider=provider(),
            institution=institution(),
            case=case(),
            today=date(2026, 7, 23),
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reasons, ())

    def test_disabled_catalog_entry_is_denied(self) -> None:
        entry = dict(APPROVED_ENTRY, enabled=False)
        decision = evaluate_assessment_access(
            catalog_entry=entry,
            provider=provider(),
            institution=institution(),
            case=case(),
            today=date(2026, 7, 23),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("catalog_entry_disabled", decision.reasons)

    def test_unresolved_license_is_denied(self) -> None:
        entry = dict(APPROVED_ENTRY, license_status="commercial_restricted")
        decision = evaluate_assessment_access(
            catalog_entry=entry,
            provider=provider(),
            institution=institution(),
            case=case(),
            today=date(2026, 7, 23),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("license_status_not_cleared", decision.reasons)

    def test_expired_professional_license_is_denied(self) -> None:
        decision = evaluate_assessment_access(
            catalog_entry=APPROVED_ENTRY,
            provider=provider(professional_license_expires=date(2026, 1, 1)),
            institution=institution(),
            case=case(),
            today=date(2026, 7, 23),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("professional_license_expired", decision.reasons)

    def test_missing_training_is_denied(self) -> None:
        decision = evaluate_assessment_access(
            catalog_entry=APPROVED_ENTRY,
            provider=provider(completed_training_ids=frozenset()),
            institution=institution(),
            case=case(),
            today=date(2026, 7, 23),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("required_training_incomplete", decision.reasons)

    def test_tool_outside_case_plan_is_denied(self) -> None:
        decision = evaluate_assessment_access(
            catalog_entry=APPROVED_ENTRY,
            provider=provider(),
            institution=institution(),
            case=case(approved_plan_tool_ids=frozenset()),
            today=date(2026, 7, 23),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("assessment_not_in_approved_case_plan", decision.reasons)

    def test_urgent_safety_level_blocks_routine_session(self) -> None:
        decision = evaluate_assessment_access(
            catalog_entry=APPROVED_ENTRY,
            provider=provider(),
            institution=institution(),
            case=case(safety_level="urgent"),
            today=date(2026, 7, 23),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("routine_assessment_blocked_by_safety_level", decision.reasons)

    def test_import_only_entry_cannot_be_administered(self) -> None:
        entry = dict(APPROVED_ENTRY, digital_right_status="results_import_only")
        decision = evaluate_assessment_access(
            catalog_entry=entry,
            provider=provider(),
            institution=institution(),
            case=case(),
            today=date(2026, 7, 23),
            mode="administration",
        )
        self.assertFalse(decision.allowed)
        self.assertIn("assessment_is_results_import_only", decision.reasons)

    def test_age_and_country_are_enforced(self) -> None:
        decision = evaluate_assessment_access(
            catalog_entry=APPROVED_ENTRY,
            provider=provider(),
            institution=institution(),
            case=case(age_months=24, country_code="XX"),
            today=date(2026, 7, 23),
        )
        self.assertFalse(decision.allowed)
        self.assertIn("case_age_outside_tool_range", decision.reasons)
        self.assertIn("tool_not_approved_for_service_country", decision.reasons)


if __name__ == "__main__":
    unittest.main()
