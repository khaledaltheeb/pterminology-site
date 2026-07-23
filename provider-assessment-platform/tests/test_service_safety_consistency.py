from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from service.provider_assessment import (
    ActorContext,
    ConflictError,
    ConsentSnapshot,
    InMemoryRepository,
    ProviderAssessmentService,
    SafetyLevel,
)


NOW = datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc)
CASE_ID = "CASE-00000001"


class PrefixCounter:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        value = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = value
        return f"{prefix}-{value:08d}"


class SafetyConsistencyTests(unittest.TestCase):
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
            assigned_case_ids=frozenset({CASE_ID}),
        )
        consent = ConsentSnapshot(
            consent_version_id="CONS-00000001",
            legal_basis="guardian_consent",
            scope=frozenset({"case_intake"}),
            obtained_at=NOW,
            withdrawal_explained=True,
            document_reference="CONSENT:DOCUMENT:TEST01",
        )
        self.service.create_case(
            actor=self.actor,
            identity_vault_reference="IDENTITY:VAULT:TEST01",
            date_of_birth=date(2016, 7, 23),
            age_months_at_intake=120,
            preferred_language="ar",
            home_languages=("ar",),
            education_languages=("ar",),
            communication_modes=("speech",),
            country_of_service="JO",
            referral_reason="Synthetic safety consistency referral reason.",
            referral_questions=("How should synthetic safety state be routed?",),
            referrer_role="guardian",
            referral_urgency="routine",
            consent=consent,
            initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
            initial_safety_actions=("no_immediate_action_required",),
            correlation_id="CORR-SAFETY-CREATE-01",
        )

    def test_monitor_event_does_not_downgrade_or_increment_urgent_case(self) -> None:
        urgent_case, _ = self.service.record_safety_event(
            actor=self.actor,
            case_id=CASE_ID,
            expected_case_version=1,
            level=SafetyLevel.URGENT,
            domains=("medical",),
            observations="Synthetic urgent observation requiring a governed hold.",
            immediate_actions=("pause_routine_pathway", "handoff_to_clinical_lead"),
            handoff_target="CLINICAL:LEAD:TEST01",
            correlation_id="CORR-SAFETY-URGENT-01",
        )
        self.assertEqual(urgent_case.version, 2)
        audit_count = len(self.repository.audit_events())

        monitored_case, monitor_event = self.service.record_safety_event(
            actor=self.actor,
            case_id=CASE_ID,
            expected_case_version=2,
            level=SafetyLevel.MONITOR,
            domains=("follow_up",),
            observations="Synthetic follow-up observation below the active urgent state.",
            immediate_actions=("continue_urgent_hold_review",),
            handoff_target=None,
            correlation_id="CORR-SAFETY-MONITOR-01",
        )

        self.assertEqual(monitor_event.level, SafetyLevel.MONITOR)
        self.assertEqual(monitored_case.version, 2)
        self.assertEqual(monitored_case.safety_level, SafetyLevel.URGENT)
        self.assertEqual(monitored_case.status.value, "safety_hold")
        self.assertEqual(len(self.repository.audit_events()), audit_count + 1)

    def test_stale_no_state_change_event_rolls_back(self) -> None:
        self.service.record_safety_event(
            actor=self.actor,
            case_id=CASE_ID,
            expected_case_version=1,
            level=SafetyLevel.URGENT,
            domains=("medical",),
            observations="Synthetic urgent observation requiring a governed hold.",
            immediate_actions=("pause_routine_pathway", "handoff_to_clinical_lead"),
            handoff_target="CLINICAL:LEAD:TEST01",
            correlation_id="CORR-SAFETY-URGENT-02",
        )
        event_count = len(self.repository.safety_events())
        audit_count = len(self.repository.audit_events())

        with self.assertRaises(ConflictError) as raised:
            self.service.record_safety_event(
                actor=self.actor,
                case_id=CASE_ID,
                expected_case_version=1,
                level=SafetyLevel.MONITOR,
                domains=("follow_up",),
                observations="Synthetic stale follow-up observation that must roll back.",
                immediate_actions=("continue_urgent_hold_review",),
                handoff_target=None,
                correlation_id="CORR-SAFETY-STALE-01",
            )

        self.assertEqual(raised.exception.code, "case_version_conflict")
        self.assertEqual(len(self.repository.safety_events()), event_count)
        self.assertEqual(len(self.repository.audit_events()), audit_count)


if __name__ == "__main__":
    unittest.main()
