from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from service.provider_assessment import (
    ActorContext,
    ConflictError,
    ConsentSnapshot,
    InMemoryRepository,
    NotFoundError,
    ProviderAssessmentService,
    ReportDraftInput,
    ReportStatus,
    ReviewInput,
    ReviewStatus,
    SafetyLevel,
)
from service.provider_assessment.repository import InMemoryRepository as NonAtomicRepository
from service.provider_assessment.transactional_repository import AtomicInMemoryRepository


FIXED_TIME = datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc)
DATE_OF_BIRTH = date(2016, 7, 23)
CASE_ID = "CASE-000001"


class PrefixCounter:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        count = self._counts.get(prefix, 0) + 1
        self._counts[prefix] = count
        return f"{prefix}-{count:06d}"


class AuditFailingRepository(AtomicInMemoryRepository):
    def append_audit_event(self, event) -> None:  # type: ignore[override]
        raise ConflictError(
            "synthetic_audit_failure",
            "Synthetic failure used to prove transaction rollback.",
        )


class ProviderServiceTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryRepository()
        self.service = ProviderAssessmentService(
            self.repository,
            id_factory=PrefixCounter(),
            clock=lambda: FIXED_TIME,
        )
        self.actor = ActorContext(
            provider_id="PROV-TEST01",
            institution_id="INST-TEST01",
            roles=frozenset(
                {
                    "provider",
                    "intake_coordinator",
                    "case_lead",
                    "clinical_reviewer",
                    "report_author",
                }
            ),
            active=True,
            professional_license_verified=True,
            professional_license_reference="LICENSE:TEST:0001",
            assigned_case_ids=frozenset({CASE_ID}),
        )
        self.consent = ConsentSnapshot(
            consent_version_id="CONS-TEST01",
            legal_basis="guardian_consent",
            scope=frozenset(
                {
                    "case_intake",
                    "multidisciplinary_review",
                    "professional_report",
                }
            ),
            obtained_at=FIXED_TIME,
            withdrawal_explained=True,
            document_reference="CONSENT:DOCUMENT:TEST01",
        )

    def create_case(self):
        case = self.service.create_case(
            actor=self.actor,
            identity_vault_reference="IDENTITY:VAULT:TEST01",
            date_of_birth=DATE_OF_BIRTH,
            age_months_at_intake=120,
            preferred_language="ar",
            home_languages=("ar",),
            education_languages=("ar", "en"),
            communication_modes=("speech", "writing"),
            country_of_service="JO",
            referral_reason="Synthetic referral reason for transaction testing.",
            referral_questions=("What support profile is currently required?",),
            referrer_role="guardian",
            referral_urgency="routine",
            consent=self.consent,
            initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
            initial_safety_actions=("no_immediate_action_required",),
            correlation_id="CORR-TEST-CREATE-0001",
        )
        self.assertEqual(case.case_id, CASE_ID)
        self.assertEqual(case.date_of_birth, DATE_OF_BIRTH)
        self.assertEqual(case.home_languages, ("ar",))
        self.assertEqual(case.education_languages, ("ar", "en"))
        self.assertEqual(case.referrer_role, "guardian")
        self.assertEqual(case.referral_urgency, "routine")
        self.assertEqual(
            case.intake_safety_actions,
            ("no_immediate_action_required",),
        )
        self.assertEqual(case.safety_screened_by, self.actor.provider_id)
        return case

    def create_approved_review(self):
        return self.service.create_team_review_version(
            actor=self.actor,
            case_id=CASE_ID,
            review_input=ReviewInput(
                review_group_id="REVIEW-GROUP-000001",
                pathway_instance_id="PATHWAY-INSTANCE-000001",
                status=ReviewStatus.APPROVED,
                member_provider_ids=("PROV-TEST01", "PROV-TEST02"),
                decision="Synthetic multidisciplinary decision for testing only.",
                supporting_evidence_ids=("EVIDENCE-000001", "EVIDENCE-000002"),
                contrary_evidence_ids=(),
                limitations="Synthetic limitations documented for transaction testing.",
                support_needs=("communication_support",),
            ),
            correlation_id="CORR-TEST-REVIEW-0001",
        )

    def test_service_rejects_repository_without_atomic_boundary(self) -> None:
        with self.assertRaises(TypeError):
            ProviderAssessmentService(NonAtomicRepository())

    def test_case_creation_rejects_age_date_mismatch(self) -> None:
        with self.assertRaises(Exception) as raised:
            self.service.create_case(
                actor=self.actor,
                identity_vault_reference="IDENTITY:VAULT:TEST99",
                date_of_birth=DATE_OF_BIRTH,
                age_months_at_intake=80,
                preferred_language="ar",
                home_languages=("ar",),
                education_languages=("ar",),
                communication_modes=("speech",),
                country_of_service="JO",
                referral_reason="Synthetic inconsistent age and date test.",
                referral_questions=("Is the age internally consistent?",),
                referrer_role="guardian",
                referral_urgency="routine",
                consent=self.consent,
                initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
                initial_safety_actions=("no_immediate_action_required",),
                correlation_id="CORR-TEST-AGE-MISMATCH",
            )
        self.assertEqual(getattr(raised.exception, "code", None), "age_date_mismatch")
        self.assertEqual(self.repository.audit_events(), ())

    def test_case_creation_rolls_back_when_audit_append_fails(self) -> None:
        repository = AuditFailingRepository()
        service = ProviderAssessmentService(
            repository,
            id_factory=PrefixCounter(),
            clock=lambda: FIXED_TIME,
        )

        with self.assertRaises(ConflictError):
            service.create_case(
                actor=self.actor,
                identity_vault_reference="IDENTITY:VAULT:TEST02",
                date_of_birth=DATE_OF_BIRTH,
                age_months_at_intake=120,
                preferred_language="ar",
                home_languages=("ar",),
                education_languages=("ar",),
                communication_modes=("speech",),
                country_of_service="JO",
                referral_reason="Synthetic referral reason that must roll back.",
                referral_questions=("Should this synthetic case persist?",),
                referrer_role="guardian",
                referral_urgency="routine",
                consent=self.consent,
                initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
                initial_safety_actions=("no_immediate_action_required",),
                correlation_id="CORR-TEST-AUDIT-FAIL",
            )

        with self.assertRaises(NotFoundError):
            repository.get_case(CASE_ID, "INST-TEST01")
        self.assertEqual(repository.audit_events(), ())

    def test_safety_event_and_case_update_roll_back_on_version_conflict(self) -> None:
        self.create_case()
        audit_count = len(self.repository.audit_events())

        with self.assertRaises(ConflictError) as raised:
            self.service.record_safety_event(
                actor=self.actor,
                case_id=CASE_ID,
                expected_case_version=99,
                level=SafetyLevel.URGENT,
                domains=("medical",),
                observations="Synthetic urgent observation that must not partially persist.",
                immediate_actions=("pause_routine_pathway", "handoff_to_clinical_lead"),
                handoff_target="CLINICAL:LEAD:TEST01",
                correlation_id="CORR-TEST-SAFETY-CONFLICT",
            )

        self.assertEqual(raised.exception.code, "case_version_conflict")
        stored = self.repository.get_case(CASE_ID, "INST-TEST01")
        self.assertEqual(stored.version, 1)
        self.assertEqual(stored.safety_level, SafetyLevel.NONE_IDENTIFIED)
        self.assertEqual(self.repository.safety_events(), ())
        self.assertEqual(len(self.repository.audit_events()), audit_count)

    def test_report_draft_rolls_back_on_case_version_conflict(self) -> None:
        self.create_case()
        review = self.create_approved_review()
        audit_count = len(self.repository.audit_events())

        with self.assertRaises(ConflictError):
            self.service.create_report_draft(
                actor=self.actor,
                case_id=CASE_ID,
                team_review_id=review.team_review_id,
                draft_input=ReportDraftInput(
                    report_id="REPORT-000001",
                    template_version="1.0.0",
                    content_reference="CONTENT:REPORT:000001",
                    content_hash="a" * 64,
                ),
                expected_case_version=99,
                correlation_id="CORR-TEST-REPORT-CONFLICT",
            )

        self.assertEqual(self.repository.reports(), ())
        self.assertEqual(len(self.repository.audit_events()), audit_count)
        self.assertEqual(
            self.repository.get_case(CASE_ID, "INST-TEST01").version,
            1,
        )

    def test_signed_report_append_rolls_back_on_case_version_conflict(self) -> None:
        self.create_case()
        review = self.create_approved_review()
        saved_case, draft = self.service.create_report_draft(
            actor=self.actor,
            case_id=CASE_ID,
            team_review_id=review.team_review_id,
            draft_input=ReportDraftInput(
                report_id="REPORT-000001",
                template_version="1.0.0",
                content_reference="CONTENT:REPORT:000001",
                content_hash="b" * 64,
            ),
            expected_case_version=1,
            correlation_id="CORR-TEST-REPORT-DRAFT",
        )
        self.assertEqual(saved_case.version, 2)
        audit_count = len(self.repository.audit_events())

        with self.assertRaises(ConflictError):
            self.service.sign_report(
                actor=self.actor,
                case_id=CASE_ID,
                draft_report_version_id=draft.report_version_id,
                confirmed_content_hash="b" * 64,
                expected_case_version=99,
                attestation="I reviewed the complete synthetic report and confirm its governed content.",
                correlation_id="CORR-TEST-SIGN-CONFLICT",
            )

        reports = self.repository.reports()
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].status, ReportStatus.DRAFT)
        self.assertEqual(len(self.repository.audit_events()), audit_count)
        self.assertEqual(
            self.repository.get_case(CASE_ID, "INST-TEST01").version,
            2,
        )


if __name__ == "__main__":
    unittest.main()
