"""Strict production-facing PostgreSQL repository facade."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from typing import Any, Iterator

from .domain import ActorContext, CaseRecord
from .errors import ConflictError, NotFoundError, PermissionDenied, ServiceError
from .postgres_repository import PostgresRepository as BasePostgresRepository


class PostgresRepository(BasePostgresRepository):
    """Final adapter facade with safe interruption and assigned-case updates."""

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
        except Exception as exc:
            connection.rollback()
            raise self._translate_database_error(exc) from exc
        except BaseException:
            connection.rollback()
            raise
        finally:
            self._state.connection = None
            self._state.actor = None
            connection.close()

    def save_case(self, case: CaseRecord, *, expected_version: int) -> CaseRecord:
        # RLS and the verified actor transaction enforce assignment. Unlike case
        # creation, an update must not require authorship by the original creator.
        self._require_transaction_institution(case.institution_id)
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
