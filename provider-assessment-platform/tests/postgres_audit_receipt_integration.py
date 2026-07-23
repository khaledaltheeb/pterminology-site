#!/usr/bin/env python3
"""Verify exact audit receipts after the PostgreSQL service integration flow."""

from __future__ import annotations

import os

import psycopg

from service.provider_assessment import (
    ActorContext,
    NotFoundError,
    PostgresRepository,
    ProviderAssessmentService,
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    app_dsn = os.environ["PA_APP_DSN"]
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
        assigned_case_ids=frozenset(
            {"CASE-SVC00000001", "CASE-SVC00000002"}
        ),
    )
    service = ProviderAssessmentService(
        PostgresRepository(lambda: psycopg.connect(app_dsn))
    )

    case_receipt = service.get_audit_receipt(
        actor=actor,
        correlation_id="CORR-SVC-CREATE-SAFETY-01",
        action="case.create",
        object_id="CASE-SVC00000001",
    )
    require(
        case_receipt.audit_event_id == "AUD-SVC00000001",
        f"Unexpected case audit receipt: {case_receipt.audit_event_id}",
    )
    require(
        case_receipt.case_id == "CASE-SVC00000001",
        "Case audit receipt is not linked to the created case",
    )

    safety_receipt = service.get_audit_receipt(
        actor=actor,
        correlation_id="CORR-SVC-SAFETY-URGENT-01",
        action="safety_event.create",
        object_id="SAFE-SVC00000001",
    )
    require(
        safety_receipt.audit_event_id == "AUD-SVC00000002",
        f"Unexpected safety audit receipt: {safety_receipt.audit_event_id}",
    )
    require(
        safety_receipt.metadata.get("routine_pathway_blocked") == "true",
        "Urgent safety receipt does not document routine pathway blocking",
    )

    signed_receipt = service.get_audit_receipt(
        actor=actor,
        correlation_id="CORR-SVC-REPORT-SIGN-01",
        action="report.sign",
        object_id="RPTV-SVC00000002",
    )
    require(
        signed_receipt.audit_event_id == "AUD-SVC00000007",
        f"Unexpected signed-report audit receipt: {signed_receipt.audit_event_id}",
    )
    require(
        signed_receipt.metadata.get("status") == "signed",
        "Signed-report receipt does not contain the signed status",
    )

    try:
        service.get_audit_receipt(
            actor=actor,
            correlation_id="CORR-SVC-REPORT-SIGN-01",
            action="report.sign",
            object_id="RPTV-NOT-EXISTING",
        )
        raise AssertionError("A nonexistent audit receipt unexpectedly resolved")
    except NotFoundError as exc:
        require(
            exc.code == "audit_receipt_not_found",
            f"Unexpected missing audit receipt code: {exc.code}",
        )

    print("PostgreSQL audit receipt lookup passed for case, urgent safety, and signed report commands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
