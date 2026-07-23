#!/usr/bin/env python3
"""Verify command, audit receipt, response snapshot, and replay in one transaction."""

from __future__ import annotations

import os
from datetime import date, datetime, timezone

import psycopg

from service.provider_assessment import (
    ActorContext,
    CommandResponse,
    ConflictError,
    ConsentSnapshot,
    DurableCommandExecutor,
    PostgresRepository,
    ProviderAssessmentService,
    SafetyLevel,
)


NOW = datetime(2026, 7, 23, 23, 30, tzinfo=timezone.utc)


class NamespacedCounter:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def __call__(self, prefix: str) -> str:
        value = self.counts.get(prefix, 0) + 1
        self.counts[prefix] = value
        return f"{prefix}-IDEM{value:08d}"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def case_request(identity_reference: str) -> dict[str, object]:
    return {
        "identity_vault_reference": identity_reference,
        "subject": {
            "date_of_birth": "2016-07-23",
            "age_months_at_intake": 120,
            "preferred_language": "ar",
            "home_languages": ["ar"],
            "education_languages": ["ar", "en"],
            "communication_modes": ["speech", "writing"],
            "country_of_service": "JO",
        },
        "consent": {
            "legal_basis": "guardian_consent",
            "scope": ["case_intake"],
            "obtained_at": "2026-07-23T23:30:00+00:00",
            "withdrawal_explained": True,
            "document_reference": "CONSENT:DOCUMENT:IDEMPOTENCY",
        },
        "referral": {
            "reason": "Synthetic durable idempotency referral reason.",
            "questions": ["Will this governed command execute exactly once?"],
            "referrer_role": "guardian",
            "urgency": "routine",
        },
        "safety": {
            "level": "none_identified",
            "actions": ["no_immediate_action_required"],
        },
    }


def create_case_command(
    *,
    service: ProviderAssessmentService,
    actor: ActorContext,
    consent_id: str,
    identity_reference: str,
    correlation_id: str,
    call_counter: dict[str, int],
) -> CommandResponse:
    call_counter["count"] = call_counter.get("count", 0) + 1
    case = service.create_case(
        actor=actor,
        identity_vault_reference=identity_reference,
        date_of_birth=date(2016, 7, 23),
        age_months_at_intake=120,
        preferred_language="ar",
        home_languages=("ar",),
        education_languages=("ar", "en"),
        communication_modes=("speech", "writing"),
        country_of_service="JO",
        referral_reason="Synthetic durable idempotency referral reason.",
        referral_questions=("Will this governed command execute exactly once?",),
        referrer_role="guardian",
        referral_urgency="routine",
        consent=ConsentSnapshot(
            consent_version_id=consent_id,
            legal_basis="guardian_consent",
            scope=frozenset({"case_intake"}),
            obtained_at=NOW,
            withdrawal_explained=True,
            document_reference="CONSENT:DOCUMENT:IDEMPOTENCY",
        ),
        initial_safety_level=SafetyLevel.NONE_IDENTIFIED,
        initial_safety_actions=("no_immediate_action_required",),
        correlation_id=correlation_id,
    )
    receipt = service.get_audit_receipt(
        actor=actor,
        correlation_id=correlation_id,
        action="case.create",
        object_id=case.case_id,
    )
    return CommandResponse(
        status=201,
        headers={
            "ETag": f'W/"case-version-{case.version}"',
            "X-Audit-Event-Id": receipt.audit_event_id,
        },
        body={
            "case_id": case.case_id,
            "version": case.version,
            "status": case.status.value,
        },
        result_object_type="case",
        result_object_id=case.case_id,
        result_version=case.version,
        audit_event_id=receipt.audit_event_id,
    )


def main() -> int:
    app_dsn = os.environ["PA_APP_DSN"]
    admin_dsn = os.environ["PA_ADMIN_DSN"]
    ids = NamespacedCounter()
    repository = PostgresRepository(
        lambda: psycopg.connect(app_dsn),
        id_factory=ids,
    )
    service = ProviderAssessmentService(
        repository,
        id_factory=ids,
        clock=lambda: NOW,
    )
    executor = DurableCommandExecutor(
        repository,
        clock=lambda: NOW,
    )
    actor = ActorContext(
        provider_id="PROV-SVC001",
        institution_id="INST-SVC001",
        roles=frozenset({"provider", "intake_coordinator", "case_lead"}),
        active=True,
        professional_license_verified=True,
        professional_license_reference="SYNTHETIC-LICENSE-SVC001",
        assigned_case_ids=frozenset(),
    )

    request_one = case_request("IDENTITY:VAULT:IDEM00000001")
    calls_one: dict[str, int] = {}
    response_one = executor.execute(
        actor=actor,
        operation="case.create",
        idempotency_key="IDEMPOTENCY-SERVICE-0001",
        request_payload=request_one,
        command=lambda: create_case_command(
            service=service,
            actor=actor,
            consent_id="CONS-IDEM00000001",
            identity_reference="IDENTITY:VAULT:IDEM00000001",
            correlation_id="CORR-IDEM-CREATE-0001",
            call_counter=calls_one,
        ),
    )
    require(not response_one.replayed, "First idempotent command was marked as replay")
    require(response_one.result_object_id == "CASE-IDEM00000001", "Unexpected first idempotent case identifier")
    require(calls_one.get("count") == 1, "First command did not execute exactly once")

    replay_one = executor.execute(
        actor=actor,
        operation="case.create",
        idempotency_key="IDEMPOTENCY-SERVICE-0001",
        request_payload=request_one,
        command=lambda: create_case_command(
            service=service,
            actor=actor,
            consent_id="CONS-IDEM-REPLAY-BLOCKED",
            identity_reference="IDENTITY:VAULT:REPLAY-BLOCKED",
            correlation_id="CORR-IDEM-REPLAY-BLOCKED",
            call_counter=calls_one,
        ),
    )
    require(replay_one.replayed, "Repeated command was not returned as replay")
    require(dict(replay_one.body) == dict(response_one.body), "Replay body changed")
    require(dict(replay_one.headers) == dict(response_one.headers), "Replay headers changed")
    require(calls_one.get("count") == 1, "Replay executed the governed command a second time")

    conflicting_request = case_request("IDENTITY:VAULT:IDEM-DIFFERENT")
    try:
        executor.execute(
            actor=actor,
            operation="case.create",
            idempotency_key="IDEMPOTENCY-SERVICE-0001",
            request_payload=conflicting_request,
            command=lambda: response_one,
        )
        raise AssertionError("Same idempotency key accepted a different request")
    except ConflictError as exc:
        require(
            exc.code == "idempotency_fingerprint_conflict",
            f"Unexpected fingerprint conflict code: {exc.code}",
        )

    request_two = case_request("IDENTITY:VAULT:IDEM00000002")
    failed_calls: dict[str, int] = {}

    def fail_after_domain_write() -> CommandResponse:
        create_case_command(
            service=service,
            actor=actor,
            consent_id="CONS-IDEM00000002",
            identity_reference="IDENTITY:VAULT:IDEM00000002",
            correlation_id="CORR-IDEM-CREATE-FAILED",
            call_counter=failed_calls,
        )
        raise ConflictError(
            "synthetic_post_write_failure",
            "Synthetic failure after domain write and before idempotency completion.",
        )

    try:
        executor.execute(
            actor=actor,
            operation="case.create",
            idempotency_key="IDEMPOTENCY-SERVICE-0002",
            request_payload=request_two,
            command=fail_after_domain_write,
        )
        raise AssertionError("Synthetic post-write failure unexpectedly committed")
    except ConflictError as exc:
        require(exc.code == "synthetic_post_write_failure", "Unexpected synthetic failure code")

    require(failed_calls.get("count") == 1, "Synthetic failed command was not invoked once")
    retry_calls: dict[str, int] = {}
    response_two = executor.execute(
        actor=actor,
        operation="case.create",
        idempotency_key="IDEMPOTENCY-SERVICE-0002",
        request_payload=request_two,
        command=lambda: create_case_command(
            service=service,
            actor=actor,
            consent_id="CONS-IDEM00000002",
            identity_reference="IDENTITY:VAULT:IDEM00000002",
            correlation_id="CORR-IDEM-CREATE-RETRY",
            call_counter=retry_calls,
        ),
    )
    require(not response_two.replayed, "Retry after rolled-back command was incorrectly replayed")
    require(response_two.result_object_id == "CASE-IDEM00000003", "Rolled-back identifier was unexpectedly reused or committed")
    require(retry_calls.get("count") == 1, "Retry did not execute exactly once")

    with psycopg.connect(admin_dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT case_id
                FROM provider_assessment.cases
                WHERE institution_id = 'INST-SVC001'
                  AND case_id LIKE 'CASE-IDEM%'
                ORDER BY case_id
                """
            )
            cases = [row[0] for row in cursor.fetchall()]
            require(
                cases == ["CASE-IDEM00000001", "CASE-IDEM00000003"],
                f"Rolled-back case or duplicate replay persisted: {cases}",
            )
            cursor.execute(
                """
                SELECT idempotency_key, state, result_object_id,
                       response_payload_hash,
                       response_headers ->> 'X-Response-Payload-Hash'
                FROM provider_assessment.idempotency_records
                WHERE institution_id = 'INST-SVC001'
                  AND provider_id = 'PROV-SVC001'
                ORDER BY idempotency_key
                """
            )
            records = cursor.fetchall()
            require(len(records) == 2, f"Expected two completed idempotency records, found {len(records)}")
            require(all(row[1] == "completed" for row in records), "An in-progress idempotency record was committed")
            require(all(row[3] == row[4] for row in records), "Stored payload hash and replay header diverged")
            cursor.execute(
                """
                SELECT count(*)
                FROM provider_assessment.audit_events
                WHERE institution_id = 'INST-SVC001'
                  AND correlation_id IN (
                      'CORR-IDEM-CREATE-0001',
                      'CORR-IDEM-CREATE-FAILED',
                      'CORR-IDEM-CREATE-RETRY'
                  )
                """
            )
            require(cursor.fetchone()[0] == 2, "Rolled-back or replayed command produced an extra audit event")

    print("Durable PostgreSQL idempotency passed: exact replay, fingerprint conflict, and post-write rollback recovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
