"""PostgreSQL repository adapter for the governed service port.

The adapter intentionally depends only on a DB-API-like connection factory. A
production deployment may use psycopg 3, but importing this module does not
require a database driver. Every public service operation must enter ``atomic``
with a verified ``ActorContext``; repository calls outside that boundary fail.
"""

from __future__ import annotations

import json
import re
import secrets
from contextlib import contextmanager
from dataclasses import replace
from threading import local
from typing import Any, Callable, Iterator, Mapping, Sequence

from .domain import (
    ActorContext,
    AuditEvent,
    CaseRecord,
    CaseStatus,
    ConsentSnapshot,
    ReportStatus,
    ReportVersion,
    ReviewStatus,
    SafetyEvent,
    SafetyLevel,
    TeamReviewVersion,
)
from .errors import (
    ConflictError,
    NotFoundError,
    PermissionDenied,
    ServiceError,
    ValidationError,
)


_INTERNAL_ID_PATTERNS = {
    "CASG": re.compile(r"^CASG-[A-Z0-9-]{8,50}$"),
    "REF": re.compile(r"^REF-[A-Z0-9-]{8,50}$"),
}


def default_repository_id_factory(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(8).upper()}"


def _json_array(values: Sequence[str] | frozenset[str]) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


def _json_object(values: Mapping[str, str]) -> str:
    return json.dumps(dict(values), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decoded_json(value: Any) -> Any:
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, memoryview):
        return json.loads(value.tobytes().decode("utf-8"))
    return value


def _string_tuple(value: Any) -> tuple[str, ...]:
    decoded = _decoded_json(value)
    if decoded is None:
        return ()
    if not isinstance(decoded, (list, tuple)):
        raise ConflictError(
            "database_json_shape_invalid",
            "A governed JSON array has an invalid database shape.",
        )
    return tuple(str(item) for item in decoded)


class PostgresRepository:
    """RLS-aware PostgreSQL implementation of the application repository port."""

    def __init__(
        self,
        connection_factory: Callable[[], Any],
        *,
        id_factory: Callable[[str], str] = default_repository_id_factory,
        statement_timeout_ms: int = 15_000,
        lock_timeout_ms: int = 5_000,
    ) -> None:
        if statement_timeout_ms <= 0 or lock_timeout_ms <= 0:
            raise ValueError("Database timeout values must be positive")
        self._connection_factory = connection_factory
        self._id_factory = id_factory
        self._statement_timeout_ms = statement_timeout_ms
        self._lock_timeout_ms = lock_timeout_ms
        self._state = local()

    @contextmanager
    def atomic(
        self,
        *,
        actor: ActorContext | None = None,
    ) -> Iterator[None]:
        if actor is None:
            raise PermissionDenied(
                "database_actor_context_required",
                "A verified actor context is required for a database transaction.",
            )
        if getattr(self._state, "connection", None) is not None:
            raise ConflictError(
                "nested_database_transaction",
                "Nested repository transactions are not supported.",
            )

        connection = self._connection_factory()
        try:
            if hasattr(connection, "autocommit"):
                connection.autocommit = False
            self._state.connection = connection
            self._state.actor = actor
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user"
                )
                role_row = cursor.fetchone()
                if role_row is None or bool(role_row[0]) or bool(role_row[1]):
                    raise PermissionDenied(
                        "unsafe_database_role",
                        "The application database role must exist and must not have SUPERUSER or BYPASSRLS.",
                    )
                cursor.execute("SET LOCAL search_path TO provider_assessment, public")
                cursor.execute("SET LOCAL row_security = on")
                cursor.execute(
                    "SELECT set_config('statement_timeout', %s, true)",
                    (f"{self._statement_timeout_ms}ms",),
                )
                cursor.execute(
                    "SELECT set_config('lock_timeout', %s, true)",
                    (f"{self._lock_timeout_ms}ms",),
                )
                cursor.execute(
                    "SELECT set_config('application_name', 'provider-assessment-service', true)"
                )
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
            yield
            connection.commit()
        except ServiceError:
            connection.rollback()
            raise
        except BaseException as exc:
            connection.rollback()
            raise self._translate_database_error(exc) from exc
        finally:
            self._state.connection = None
            self._state.actor = None
            connection.close()

    def add_case(self, case: CaseRecord) -> None:
        actor = self._actor()
        self._require_case_write_scope(case, actor)
        if case.date_of_birth is None or case.safety_screened_at is None:
            raise ValidationError(
                "incomplete_case_intake",
                "Date of birth and the intake safety timestamp are required for PostgreSQL storage.",
            )
        if not case.safety_screened_by or not case.intake_safety_actions:
            raise ValidationError(
                "incomplete_case_safety_snapshot",
                "The intake safety screener and action or no-action decision are required.",
            )
        if case.consent.withdrawn_at is not None and case.consent.withdrawn_at <= case.created_at:
            raise ValidationError(
                "withdrawn_intake_consent",
                "A case cannot be created from consent already withdrawn at intake.",
            )

        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO cases (
                    case_id, institution_id, identity_vault_reference, status,
                    date_of_birth, age_months_at_intake, preferred_language,
                    home_languages, education_languages, communication_modes,
                    country_of_service, safety_level, current_pathway_id,
                    current_pathway_version, assigned_case_lead_provider_id,
                    created_by_provider_id, created_at, updated_at,
                    safety_screened_at, safety_screened_by_provider_id,
                    intake_safety_actions
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s::jsonb,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                )
                """,
                (
                    case.case_id,
                    case.institution_id,
                    case.identity_vault_reference,
                    case.status.value,
                    case.date_of_birth,
                    case.age_months_at_intake,
                    case.preferred_language,
                    _json_array(case.home_languages),
                    _json_array(case.education_languages),
                    _json_array(case.communication_modes),
                    case.country_of_service,
                    case.safety_level.value,
                    case.current_pathway_id,
                    case.current_pathway_version,
                    case.assigned_case_lead_provider_id,
                    case.created_by_provider_id,
                    case.created_at,
                    case.updated_at,
                    case.safety_screened_at,
                    case.safety_screened_by,
                    _json_array(case.intake_safety_actions),
                ),
            )

            assignment_role = (
                "case_lead"
                if case.assigned_case_lead_provider_id == actor.provider_id
                else "intake_coordinator"
            )
            cursor.execute(
                """
                INSERT INTO case_assignments (
                    case_assignment_id, institution_id, case_id, provider_id,
                    assignment_role, active, assigned_at, assigned_by_provider_id
                ) VALUES (%s, %s, %s, %s, %s, true, %s, %s)
                """,
                (
                    self._new_internal_id("CASG"),
                    case.institution_id,
                    case.case_id,
                    actor.provider_id,
                    assignment_role,
                    case.created_at,
                    actor.provider_id,
                ),
            )

            cursor.execute(
                """
                INSERT INTO consent_versions (
                    consent_version_id, institution_id, case_id, version,
                    legal_basis, scope, obtained_at, withdrawal_explained,
                    withdrawn_at, document_reference, created_by_provider_id,
                    created_at, supersedes_consent_version_id
                ) VALUES (
                    %s, %s, %s, 1, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, NULL
                )
                """,
                (
                    case.consent.consent_version_id,
                    case.institution_id,
                    case.case_id,
                    case.consent.legal_basis,
                    _json_array(case.consent.scope),
                    case.consent.obtained_at,
                    case.consent.withdrawal_explained,
                    case.consent.withdrawn_at,
                    case.consent.document_reference,
                    actor.provider_id,
                    case.created_at,
                ),
            )

            cursor.execute(
                """
                INSERT INTO referrals (
                    referral_id, institution_id, case_id, reason, questions,
                    referrer_role, urgency, received_at,
                    created_by_provider_id, created_at
                ) VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                """,
                (
                    self._new_internal_id("REF"),
                    case.institution_id,
                    case.case_id,
                    case.referral_reason,
                    _json_array(case.referral_questions),
                    case.referrer_role,
                    case.referral_urgency,
                    case.created_at,
                    actor.provider_id,
                    case.created_at,
                ),
            )

    def get_case(self, case_id: str, institution_id: str) -> CaseRecord:
        self._require_transaction_institution(institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT case_id, institution_id, identity_vault_reference, version,
                       status, date_of_birth, age_months_at_intake,
                       preferred_language, home_languages, education_languages,
                       communication_modes, country_of_service, safety_level,
                       current_pathway_id, current_pathway_version,
                       created_by_provider_id, assigned_case_lead_provider_id,
                       created_at, updated_at, safety_screened_at,
                       safety_screened_by_provider_id, intake_safety_actions
                FROM cases
                WHERE case_id = %s AND institution_id = %s
                """,
                (case_id, institution_id),
            )
            case_row = cursor.fetchone()
            if case_row is None:
                raise NotFoundError(
                    "case_not_found",
                    "The case was not found inside the authorized institution and assignment scope.",
                    {"case_id": case_id},
                )

            cursor.execute(
                """
                SELECT consent_version_id, legal_basis, scope, obtained_at,
                       withdrawal_explained, document_reference, withdrawn_at
                FROM current_consents
                WHERE case_id = %s AND institution_id = %s
                """,
                (case_id, institution_id),
            )
            consent_row = cursor.fetchone()
            cursor.execute(
                """
                SELECT reason, questions, referrer_role, urgency
                FROM referrals
                WHERE case_id = %s AND institution_id = %s
                ORDER BY created_at DESC, referral_id DESC
                LIMIT 1
                """,
                (case_id, institution_id),
            )
            referral_row = cursor.fetchone()

        if consent_row is None or referral_row is None:
            raise ConflictError(
                "case_record_incomplete",
                "The case is missing its current consent or referral record.",
                {"case_id": case_id},
            )

        consent = ConsentSnapshot(
            consent_version_id=consent_row[0],
            legal_basis=consent_row[1],
            scope=frozenset(_string_tuple(consent_row[2])),
            obtained_at=consent_row[3],
            withdrawal_explained=bool(consent_row[4]),
            document_reference=consent_row[5],
            withdrawn_at=consent_row[6],
        )
        return CaseRecord(
            case_id=case_row[0],
            institution_id=case_row[1],
            identity_vault_reference=case_row[2],
            version=int(case_row[3]),
            status=CaseStatus(case_row[4]),
            date_of_birth=case_row[5],
            age_months_at_intake=int(case_row[6]),
            preferred_language=case_row[7],
            home_languages=_string_tuple(case_row[8]),
            education_languages=_string_tuple(case_row[9]),
            communication_modes=_string_tuple(case_row[10]),
            country_of_service=case_row[11],
            safety_level=SafetyLevel(case_row[12]),
            current_pathway_id=case_row[13],
            current_pathway_version=case_row[14],
            created_by_provider_id=case_row[15],
            assigned_case_lead_provider_id=case_row[16],
            created_at=case_row[17],
            updated_at=case_row[18],
            safety_screened_at=case_row[19],
            safety_screened_by=case_row[20],
            intake_safety_actions=_string_tuple(case_row[21]),
            referral_reason=referral_row[0],
            referral_questions=_string_tuple(referral_row[1]),
            referrer_role=referral_row[2],
            referral_urgency=referral_row[3],
            consent=consent,
        )

    def save_case(self, case: CaseRecord, *, expected_version: int) -> CaseRecord:
        self._require_case_write_scope(case, self._actor())
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE cases
                SET status = %s,
                    safety_level = %s,
                    current_pathway_id = %s,
                    current_pathway_version = %s,
                    assigned_case_lead_provider_id = %s
                WHERE case_id = %s
                  AND institution_id = %s
                  AND version = %s
                RETURNING version, updated_at
                """,
                (
                    case.status.value,
                    case.safety_level.value,
                    case.current_pathway_id,
                    case.current_pathway_version,
                    case.assigned_case_lead_provider_id,
                    case.case_id,
                    case.institution_id,
                    expected_version,
                ),
            )
            row = cursor.fetchone()
            if row is not None:
                return replace(case, version=int(row[0]), updated_at=row[1])

            cursor.execute(
                "SELECT version FROM cases WHERE case_id = %s AND institution_id = %s",
                (case.case_id, case.institution_id),
            )
            current = cursor.fetchone()
            if current is None:
                raise NotFoundError(
                    "case_not_found",
                    "The case was not found inside the authorized assignment scope.",
                    {"case_id": case.case_id},
                )
            raise ConflictError(
                "case_version_conflict",
                "The case changed after it was read; reload before applying the update.",
                {
                    "case_id": case.case_id,
                    "expected_version": expected_version,
                    "current_version": int(current[0]),
                },
            )

    def append_safety_event(self, event: SafetyEvent) -> None:
        self._require_transaction_institution(event.institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO safety_events (
                    safety_event_id, institution_id, case_id, level, domains,
                    observations, immediate_actions, handoff_target,
                    routine_pathway_blocked, created_by_provider_id, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s, %s, %s
                )
                """,
                (
                    event.safety_event_id,
                    event.institution_id,
                    event.case_id,
                    event.level.value,
                    _json_array(event.domains),
                    event.observations,
                    _json_array(event.immediate_actions),
                    event.handoff_target,
                    event.routine_pathway_blocked,
                    event.created_by_provider_id,
                    event.created_at,
                ),
            )

    def append_team_review(self, review: TeamReviewVersion) -> None:
        self._require_transaction_institution(review.institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO team_reviews (
                    team_review_id, institution_id, case_id,
                    pathway_instance_id, status, member_provider_ids,
                    decision, supporting_evidence_ids, contrary_evidence_ids,
                    limitations, support_needs, approved_by_provider_id,
                    approved_at, created_at, review_group_id, version,
                    supersedes_team_review_id, created_by_provider_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s::jsonb, %s,
                    %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    review.team_review_id,
                    review.institution_id,
                    review.case_id,
                    review.pathway_instance_id,
                    review.status.value,
                    _json_array(review.member_provider_ids),
                    review.decision,
                    _json_array(review.supporting_evidence_ids),
                    _json_array(review.contrary_evidence_ids),
                    review.limitations,
                    _json_array(review.support_needs),
                    review.approved_by_provider_id,
                    review.approved_at,
                    review.created_at,
                    review.review_group_id,
                    review.version,
                    review.supersedes_team_review_id,
                    review.created_by_provider_id,
                ),
            )

    def get_team_review(
        self,
        review_id: str,
        institution_id: str,
        case_id: str,
    ) -> TeamReviewVersion:
        self._require_transaction_institution(institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                self._review_select_sql()
                + " WHERE team_review_id = %s AND institution_id = %s AND case_id = %s",
                (review_id, institution_id, case_id),
            )
            row = cursor.fetchone()
        if row is None:
            raise NotFoundError(
                "team_review_not_found",
                "The team review was not found inside the authorized case scope.",
                {"team_review_id": review_id},
            )
        return self._review_from_row(row)

    def get_latest_team_review(
        self,
        review_group_id: str,
        institution_id: str,
        case_id: str,
    ) -> TeamReviewVersion | None:
        self._require_transaction_institution(institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                self._review_select_sql()
                + " WHERE review_group_id = %s AND institution_id = %s AND case_id = %s"
                + " ORDER BY version DESC LIMIT 1",
                (review_group_id, institution_id, case_id),
            )
            row = cursor.fetchone()
        return None if row is None else self._review_from_row(row)

    def append_report(self, report: ReportVersion) -> None:
        self._require_transaction_institution(report.institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO report_versions (
                    report_version_id, report_id, institution_id, case_id,
                    team_review_id, version, status, template_version,
                    content_reference, content_hash, human_review_required,
                    professional_license_reference, signed_by_provider_id,
                    signed_at, created_by_provider_id, created_at,
                    supersedes_report_version_id, withdrawal_reason
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    report.report_version_id,
                    report.report_id,
                    report.institution_id,
                    report.case_id,
                    report.team_review_id,
                    report.version,
                    report.status.value,
                    report.template_version,
                    report.content_reference,
                    report.content_hash,
                    report.human_review_required,
                    report.professional_license_reference,
                    report.signed_by_provider_id,
                    report.signed_at,
                    report.created_by_provider_id,
                    report.created_at,
                    report.supersedes_report_version_id,
                    report.withdrawal_reason,
                ),
            )

    def get_report_version(
        self,
        report_version_id: str,
        institution_id: str,
        case_id: str,
    ) -> ReportVersion:
        self._require_transaction_institution(institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                self._report_select_sql()
                + " WHERE report_version_id = %s AND institution_id = %s AND case_id = %s",
                (report_version_id, institution_id, case_id),
            )
            row = cursor.fetchone()
        if row is None:
            raise NotFoundError(
                "report_not_found",
                "The report was not found inside the authorized case scope.",
                {"report_version_id": report_version_id},
            )
        return self._report_from_row(row)

    def get_latest_report(
        self,
        report_id: str,
        institution_id: str,
        case_id: str,
    ) -> ReportVersion | None:
        self._require_transaction_institution(institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                self._report_select_sql()
                + " WHERE report_id = %s AND institution_id = %s AND case_id = %s"
                + " ORDER BY version DESC LIMIT 1",
                (report_id, institution_id, case_id),
            )
            row = cursor.fetchone()
        return None if row is None else self._report_from_row(row)

    def append_audit_event(self, event: AuditEvent) -> None:
        self._require_transaction_institution(event.institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO audit_events (
                    audit_event_id, institution_id, case_id,
                    actor_provider_id, occurred_at, action, object_type,
                    object_id, reason, correlation_id, previous_event_hash,
                    event_hash, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s::jsonb
                )
                """,
                (
                    event.audit_event_id,
                    event.institution_id,
                    event.case_id,
                    event.actor_provider_id,
                    event.occurred_at,
                    event.action,
                    event.object_type,
                    event.object_id,
                    event.reason,
                    event.correlation_id,
                    event.previous_event_hash,
                    event.event_hash,
                    _json_object(event.metadata),
                ),
            )

    def last_audit_hash(self, institution_id: str) -> str | None:
        self._require_transaction_institution(institution_id)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_institution_last_audit_hash()")
            row = cursor.fetchone()
        return None if row is None else row[0]

    def _connection(self) -> Any:
        connection = getattr(self._state, "connection", None)
        if connection is None:
            raise ConflictError(
                "database_transaction_required",
                "Repository access is allowed only inside an atomic service transaction.",
            )
        return connection

    def _actor(self) -> ActorContext:
        actor = getattr(self._state, "actor", None)
        if actor is None:
            raise PermissionDenied(
                "database_actor_context_required",
                "A verified actor context is required for repository access.",
            )
        return actor

    def _require_transaction_institution(self, institution_id: str) -> None:
        actor = self._actor()
        if actor.institution_id != institution_id:
            raise PermissionDenied(
                "database_institution_scope_mismatch",
                "Repository operation does not match the transaction institution.",
            )

    def _require_case_write_scope(self, case: CaseRecord, actor: ActorContext) -> None:
        self._require_transaction_institution(case.institution_id)
        if case.created_by_provider_id != actor.provider_id and actor.audit_scope != "institution":
            raise PermissionDenied(
                "database_case_creator_mismatch",
                "The case creator must match the authenticated provider.",
            )
        if case.safety_screened_by != actor.provider_id and actor.audit_scope != "institution":
            raise PermissionDenied(
                "database_safety_screener_mismatch",
                "The intake safety screener must match the authenticated provider.",
            )
        if case.assigned_case_lead_provider_id not in {None, actor.provider_id}:
            raise ValidationError(
                "unsupported_initial_case_lead",
                "The initial case lead must be the authenticated provider or remain unassigned.",
            )

    def _new_internal_id(self, prefix: str) -> str:
        value = self._id_factory(prefix)
        pattern = _INTERNAL_ID_PATTERNS.get(prefix)
        if pattern is None or not pattern.fullmatch(value):
            raise ValidationError(
                "invalid_repository_identifier",
                "The repository identifier factory produced an incompatible identifier.",
                {"prefix": prefix},
            )
        return value

    @staticmethod
    def _review_select_sql() -> str:
        return """
            SELECT team_review_id, review_group_id, case_id, institution_id,
                   pathway_instance_id, version, status, member_provider_ids,
                   decision, supporting_evidence_ids, contrary_evidence_ids,
                   limitations, support_needs, created_by_provider_id,
                   approved_by_provider_id, approved_at,
                   supersedes_team_review_id, created_at
            FROM team_reviews
        """

    @staticmethod
    def _review_from_row(row: Sequence[Any]) -> TeamReviewVersion:
        return TeamReviewVersion(
            team_review_id=row[0],
            review_group_id=row[1],
            case_id=row[2],
            institution_id=row[3],
            pathway_instance_id=row[4],
            version=int(row[5]),
            status=ReviewStatus(row[6]),
            member_provider_ids=_string_tuple(row[7]),
            decision=row[8],
            supporting_evidence_ids=_string_tuple(row[9]),
            contrary_evidence_ids=_string_tuple(row[10]),
            limitations=row[11],
            support_needs=_string_tuple(row[12]),
            created_by_provider_id=row[13],
            approved_by_provider_id=row[14],
            approved_at=row[15],
            supersedes_team_review_id=row[16],
            created_at=row[17],
        )

    @staticmethod
    def _report_select_sql() -> str:
        return """
            SELECT report_version_id, report_id, case_id, institution_id,
                   team_review_id, version, status, template_version,
                   content_reference, content_hash, created_by_provider_id,
                   human_review_required, signed_by_provider_id,
                   professional_license_reference, signed_at,
                   supersedes_report_version_id, withdrawal_reason, created_at
            FROM report_versions
        """

    @staticmethod
    def _report_from_row(row: Sequence[Any]) -> ReportVersion:
        return ReportVersion(
            report_version_id=row[0],
            report_id=row[1],
            case_id=row[2],
            institution_id=row[3],
            team_review_id=row[4],
            version=int(row[5]),
            status=ReportStatus(row[6]),
            template_version=row[7],
            content_reference=row[8],
            content_hash=row[9],
            created_by_provider_id=row[10],
            human_review_required=bool(row[11]),
            signed_by_provider_id=row[12],
            professional_license_reference=row[13],
            signed_at=row[14],
            supersedes_report_version_id=row[15],
            withdrawal_reason=row[16],
            created_at=row[17],
        )

    @staticmethod
    def _translate_database_error(exc: BaseException) -> ServiceError:
        sqlstate = getattr(exc, "sqlstate", None)
        if sqlstate in {"40001", "40P01", "55P03", "57014"}:
            return ConflictError(
                "database_concurrency_conflict",
                "The database transaction could not complete safely; retry with a fresh state.",
            )
        if sqlstate == "23505":
            return ConflictError(
                "database_unique_conflict",
                "A governed immutable identifier or version already exists.",
            )
        if sqlstate == "42501":
            return PermissionDenied(
                "database_permission_denied",
                "The database rejected the operation under row-level security.",
            )
        if sqlstate in {"23503", "23514", "22P02", "22001", "22007"}:
            return ValidationError(
                "database_invariant_rejected",
                "The database rejected data that violates a governed invariant.",
            )
        return ConflictError(
            "database_operation_failed",
            "The database operation failed without exposing protected implementation details.",
        )
