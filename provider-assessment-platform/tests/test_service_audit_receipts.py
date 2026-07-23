from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from service.provider_assessment import (
    ActorContext,
    ConsentSnapshot,
    InMemoryRepository,
    NotFoundError,
    ProviderAssessmentService,
    SafetyLevel,
)


NOW = datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc)


class PrefixCounter:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        value = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = value
        return f"{prefix}-{value:08d}"


class AuditReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRepository()
        self.service = ProviderAssessmentService(
            self.repository,
            id_factory=PrefixCounter(),
            clock=lambda: NOW,
        )
        self.actor = ActorContext(
            provider_id="PROV-TEST01",
            institution_id="INST-TEST01",
            roles=frozenset({"provider", "intake_coordinator", "case_lead"}),
            active=True,
            professional_license_verified=True,
            professional_license_reference="LICENSE:TEST:0001",
            assigned_case_ids=frozenset({"CASE-00000001"}),
        )
        self.consent = ConsentSnapshot(
            consent_version_id="CONS-00000001",
            legal_basis="guardian_consent",
            scope=frozenset({"case_intake"}),
            obtained_at=NOW,
            withdrawal_explained=True,
            document_reference="CONSENT:DOCUMENT:TEST01",
        )

    def test_create_case_receipt_is_exact_and_retrievable(self) -> None:
        case = self.service.create_case(
            actor=self.actor,
            identity_vault_reference="IDENTITY:VAULT:TEST01",
            date_of_birth=date(2016, 7, 23),
            age_months_at_intake=120,
            preferred_language="ar",
            home_languages=("ar",),
            education_languages=("ar",),
            communication_modes=("speech",),
            country_of_service="JO",
            referral_reason="Synthetic referral reason for audit receipt verification.",
            referral_questions=("Which synthetic support should be documented?",),
            referrer_role="guardian",
            referral_urgency="routine",
            consent=self.consent,
            initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
            initial_safety_actions=("no_immediate_action_required",),
            correlation_id="CORR-AUDIT-RECEIPT-01",
        )

        receipt = self.service.get_audit_receipt(
            actor=self.actor,
            correlation_id="CORR-AUDIT-RECEIPT-01",
            action="case.create",
            object_id=case.case_id,
        )
        self.assertEqual(receipt.audit_event_id, "AUD-00000001")
        self.assertEqual(receipt.case_id, case.case_id)
        self.assertEqual(receipt.metadata.get("status"), "intake")

    def test_incorrect_selector_does_not_return_nearby_receipt(self) -> None:
        case = self.service.create_case(
            actor=self.actor,
            identity_vault_reference="IDENTITY:VAULT:TEST02",
            date_of_birth=date(2016, 7, 23),
            age_months_at_intake=120,
            preferred_language="ar",
            home_languages=("ar",),
            education_languages=("ar",),
            communication_modes=("speech",),
            country_of_service="JO",
            referral_reason="Synthetic referral reason for missing receipt verification.",
            referral_questions=("Will an incorrect object selector be rejected?",),
            referrer_role="guardian",
            referral_urgency="routine",
            consent=self.consent,
            initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
            initial_safety_actions=("no_immediate_action_required",),
            correlation_id="CORR-AUDIT-RECEIPT-02",
        )

        with self.assertRaises(NotFoundError) as raised:
            self.service.get_audit_receipt(
                actor=self.actor,
                correlation_id="CORR-AUDIT-RECEIPT-02",
                action="case.create",
                object_id=case.case_id + "-OTHER",
            )
        self.assertEqual(raised.exception.code, "audit_receipt_not_found")


if __name__ == "__main__":
    unittest.main()
