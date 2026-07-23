#!/usr/bin/env python3
"""Run the governed application service against a real PostgreSQL test database."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone

import psycopg

from service.provider_assessment import (
    ActorContext,
    ConflictError,
    ConsentSnapshot,
    PostgresRepository,
    ProviderAssessmentService,
    ReportDraftInput,
    ReportStatus,
    ReviewInput,
    ReviewStatus,
    SafetyLevel,
)


NOW = datetime(2026, 7, 23, 22, 0, tzinfo=timezone.utc)
SAFETY_CASE_ID = "CASE-SVC00000001"
REPORT_CASE_ID = "CASE-SVC00000002"


class PrefixCounter:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        value = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = value
        return f"{prefix}-SVC{value:08d}"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def set_actor_context(connection: psycopg.Connection, actor: ActorContext) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL search_path TO provider_assessment, public")
        cursor.execute("SET LOCAL row_security = on")
        cursor.execute(
            "SELECT set_config('app.institution_id', %s, true)",
            (actor.institution_id,),
        )
        cursor.execute(
            "SELECT set_config('app.provider_id', %s, true)",
            (actor.provider_id,),
        )
        cursor.execute(
            "SELECT set_config('app.audit_scope', %s, true)",
            (actor.audit_scope or "",),
        )


def create_case(
    service: ProviderAssessmentService,
    actor: ActorContext,
    *,
    consent_id: str,
    identity_reference: str,
    correlation_id: str,
):
    return service.create_case(
        actor=actor,
        identity_vault_reference=identity_reference,
        date_of_birth=date(2016, 7, 23),
        age_months_at_intake=120,
        preferred_language="ar",
        home_languages=("ar",),
        education_languages=("ar", "en"),
        communication_modes=("speech", "writing"),
        country_of_service="JO",
        referral_reason="Synthetic integrated referral for governed service verification.",
        referral_questions=(
            "What synthetic support profile should the governed workflow document?",
        ),
        referrer_role="guardian",
        referral_urgency="routine",
        consent=ConsentSnapshot(
            consent_version_id=consent_id,
            legal_basis="guardian_consent",
            scope=frozenset(
                {
                    "case_intake",
                    "multidisciplinary_review",
                    "professional_report",
                }
            ),
            obtained_at=NOW,
            withdrawal_explained=True,
            document_reference=f"CONSENT:DOCUMENT:{consent_id}",
        ),
        initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
        initial_safety_actions=("no_immediate_action_required",),
        correlation_id=correlation_id,
    )


def main() -> int:
    app_dsn = os.environ["PA_APP_DSN"]
    admin_dsn = os.environ["PA_ADMIN_DSN"]
    counter = PrefixCounter()
    repository = PostgresRepository(
        lambda: psycopg.connect(app_dsn),
        id_factory=counter,
    )
    service = ProviderAssessmentService(
        repository,
        id_factory=counter,
        clock=lambda: NOW,
    )
    actor = ActorContext(
        provider_id="PROV-SVC001",
        institution_id="INST-SVC001",
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
        professional_license_reference="SYNTHETIC-LICENSE-SVC001",
        assigned_case_ids=frozenset({SAFETY_CASE_ID, REPORT_CASE_ID}),
    )

    safety_case = create_case(
        service,
        actor,
        consent_id="CONS-SVC00000001",
        identity_reference="IDENTITY:VAULT:SVC00000001",
        correlation_id="CORR-SVC-CREATE-SAFETY-01",
    )
    require(safety_case.case_id == SAFETY_CASE_ID, "Unexpected safety case identifier")
    require(safety_case.version == 1, "New case must start at version 1")

    urgent_case, urgent_event = service.record_safety_event(
        actor=actor,
        case_id=SAFETY_CASE_ID,
        expected_case_version=1,
        level=SafetyLevel.URGENT,
        domains=("medical",),
        observations="Synthetic urgent observation for PostgreSQL service integration.",
        immediate_actions=("pause_routine_pathway", "handoff_to_clinical_lead"),
        handoff_target="CLINICAL:LEAD:SVC001",
        correlation_id="CORR-SVC-SAFETY-URGENT-01",
    )
    require(urgent_case.version == 2, "Urgent state change must increment the case once")
    require(urgent_case.safety_level is SafetyLevel.URGENT, "Urgent safety level was not persisted")
    require(urgent_event.routine_pathway_blocked, "Urgent event must block routine routing")

    monitored_case, _ = service.record_safety_event(
        actor=actor,
        case_id=SAFETY_CASE_ID,
        expected_case_version=2,
        level=SafetyLevel.MONITOR,
        domains=("follow_up",),
        observations="Synthetic monitor observation below an existing urgent state.",
        immediate_actions=("continue_urgent_hold_review",),
        handoff_target=None,
        correlation_id="CORR-SVC-SAFETY-MONITOR-01",
    )
    require(monitored_case.version == 2, "No-op monitor event must not increment case version")
    require(monitored_case.safety_level is SafetyLevel.URGENT, "Monitor event downgraded urgent state")

    with psycopg.connect(admin_dsn) as admin_connection:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT version, status, safety_level
                FROM provider_assessment.cases
                WHERE institution_id = 'INST-SVC001'
                  AND case_id = %s
                """,
                (SAFETY_CASE_ID,),
            )
            database_case = cursor.fetchone()
            require(database_case == (2, "safety_hold", "urgent"), f"Unexpected database safety case state: {database_case}")
            cursor.execute(
                """
                SELECT count(*)
                FROM provider_assessment.safety_events
                WHERE institution_id = 'INST-SVC001'
                  AND case_id = %s
                """,
                (SAFETY_CASE_ID,),
            )
            require(cursor.fetchone()[0] == 2, "Two immutable safety events were expected")

    event_count_before_conflict: int
    with psycopg.connect(admin_dsn) as admin_connection:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM provider_assessment.safety_events WHERE institution_id = 'INST-SVC001' AND case_id = %s",
                (SAFETY_CASE_ID,),
            )
            event_count_before_conflict = cursor.fetchone()[0]
    try:
        service.record_safety_event(
            actor=actor,
            case_id=SAFETY_CASE_ID,
            expected_case_version=1,
            level=SafetyLevel.MONITOR,
            domains=("follow_up",),
            observations="Synthetic stale safety event that must roll back completely.",
            immediate_actions=("continue_urgent_hold_review",),
            handoff_target=None,
            correlation_id="CORR-SVC-SAFETY-STALE-01",
        )
        raise AssertionError("Stale safety event unexpectedly succeeded")
    except ConflictError as exc:
        require(exc.code == "case_version_conflict", f"Unexpected conflict code: {exc.code}")
    with psycopg.connect(admin_dsn) as admin_connection:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM provider_assessment.safety_events WHERE institution_id = 'INST-SVC001' AND case_id = %s",
                (SAFETY_CASE_ID,),
            )
            require(cursor.fetchone()[0] == event_count_before_conflict, "Rolled-back safety event persisted")

    report_case = create_case(
        service,
        actor,
        consent_id="CONS-SVC00000002",
        identity_reference="IDENTITY:VAULT:SVC00000002",
        correlation_id="CORR-SVC-CREATE-REPORT-01",
    )
    require(report_case.case_id == REPORT_CASE_ID, "Unexpected report case identifier")

    with psycopg.connect(app_dsn) as app_connection:
        set_actor_context(app_connection, actor)
        with app_connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO provider_assessment.pathway_instances (
                    pathway_instance_id, institution_id, case_id,
                    pathway_id, pathway_version, pathway_definition_hash,
                    current_node_id, status, started_by_provider_id, started_at
                ) VALUES (
                    'PTH-SVC00000001', 'INST-SVC001', %s,
                    'developmental-intake', '0.1.0', %s,
                    'multidisciplinary-review', 'active', 'PROV-SVC001', %s
                )
                """,
                (REPORT_CASE_ID, "d" * 64, NOW),
            )

    review = service.create_team_review_version(
        actor=actor,
        case_id=REPORT_CASE_ID,
        review_input=ReviewInput(
            review_group_id="TREVG-SVC00000001",
            pathway_instance_id="PTH-SVC00000001",
            status=ReviewStatus.APPROVED,
            member_provider_ids=("PROV-SVC001", "PROV-SVC002"),
            decision="Synthetic approved multidisciplinary decision for integration testing.",
            supporting_evidence_ids=("EVIDENCE-SVC000001", "EVIDENCE-SVC000002"),
            contrary_evidence_ids=(),
            limitations="Synthetic limitations are explicit and prohibit clinical interpretation.",
            support_needs=("communication_support", "environmental_accommodation"),
        ),
        correlation_id="CORR-SVC-REVIEW-01",
    )
    require(review.status is ReviewStatus.APPROVED, "Team review was not approved")
    require(review.version == 1, "First review must be version 1")

    report_case, draft = service.create_report_draft(
        actor=actor,
        case_id=REPORT_CASE_ID,
        team_review_id=review.team_review_id,
        draft_input=ReportDraftInput(
            report_id="RPT-SVC00000001",
            template_version="1.0.0",
            content_reference="CONTENT:REPORT:SVC00000001",
            content_hash="e" * 64,
        ),
        expected_case_version=1,
        correlation_id="CORR-SVC-REPORT-DRAFT-01",
    )
    require(report_case.version == 2, "Report draft must increment case version")
    require(draft.status is ReportStatus.DRAFT, "Report draft status mismatch")

    approved_case, signed = service.sign_report(
        actor=actor,
        case_id=REPORT_CASE_ID,
        draft_report_version_id=draft.report_version_id,
        confirmed_content_hash="e" * 64,
        expected_case_version=2,
        attestation="I reviewed the complete synthetic report and confirm the governed content hash.",
        correlation_id="CORR-SVC-REPORT-SIGN-01",
    )
    require(approved_case.version == 3, "Report signing must increment case version")
    require(approved_case.status.value == "approved", "Signed report did not approve the case workflow")
    require(signed.status is ReportStatus.SIGNED, "Signed report status mismatch")
    require(signed.version == 2, "Signed report must be append-only version 2")

    with psycopg.connect(admin_dsn) as admin_connection:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT report_id, version, status, professional_license_reference
                FROM provider_assessment.current_reports
                WHERE institution_id = 'INST-SVC001'
                  AND case_id = %s
                """,
                (REPORT_CASE_ID,),
            )
            latest_report = cursor.fetchone()
            require(
                latest_report == (
                    "RPT-SVC00000001",
                    2,
                    "signed",
                    "SYNTHETIC-LICENSE-SVC001",
                ),
                f"Unexpected latest report: {latest_report}",
            )
            cursor.execute(
                """
                SELECT previous_event_hash, event_hash
                FROM provider_assessment.audit_events
                WHERE institution_id = 'INST-SVC001'
                ORDER BY occurred_at, audit_event_id
                """
            )
            audit_rows = cursor.fetchall()
            require(len(audit_rows) == 7, f"Expected seven audit events, found {len(audit_rows)}")
            previous = None
            for previous_hash, event_hash in audit_rows:
                require(previous_hash == previous, "Database audit chain contains a fork or gap")
                previous = event_hash

    unassigned_actor = ActorContext(
        provider_id="PROV-SVC002",
        institution_id="INST-SVC001",
        roles=frozenset({"provider", "clinical_reviewer"}),
        active=True,
        professional_license_verified=True,
        professional_license_reference="SYNTHETIC-LICENSE-SVC002",
        assigned_case_ids=frozenset(),
    )
    with psycopg.connect(app_dsn) as app_connection:
        set_actor_context(app_connection, unassigned_actor)
        with app_connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM provider_assessment.cases")
            require(cursor.fetchone()[0] == 0, "Unassigned provider could see protected cases")

    print("PostgreSQL governed service integration passed: intake, RLS, safety, audit, review, draft, and signed report.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
