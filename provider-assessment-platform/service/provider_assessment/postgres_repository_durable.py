"""Durable PostgreSQL repository with one outer command transaction."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, Mapping

from .domain import ActorContext
from .durable_idempotency import CommandResponse, sha256_json
from .errors import ConflictError, PermissionDenied, ServiceError
from .postgres_repository_strict import PostgresRepository as StrictPostgresRepository


def _json_object(value: Mapping[str, Any]) -> str:
    return json.dumps(
        dict(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _decoded_object(value: Any, *, field: str) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    elif isinstance(value, memoryview):
        value = json.loads(value.tobytes().decode("utf-8"))
    if not isinstance(value, dict):
        raise ConflictError(
            "idempotency_snapshot_invalid",
            "A persisted idempotency response has an invalid JSON object shape.",
            {"field": field},
        )
    return value


class PostgresRepository(StrictPostgresRepository):
    """Final adapter supporting nested service scopes and durable command replay."""

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

        existing_connection = getattr(self._state, "connection", None)
        if existing_connection is not None:
            existing_actor = getattr(self._state, "actor", None)
            if (
                existing_actor is None
                or existing_actor.institution_id != actor.institution_id
                or existing_actor.provider_id != actor.provider_id
                or existing_actor.audit_scope != actor.audit_scope
            ):
                raise PermissionDenied(
                    "nested_database_actor_mismatch",
                    "Nested repository access must use the same verified actor and institution.",
                )
            self._state.depth = int(getattr(self._state, "depth", 1)) + 1
            try:
                yield
            finally:
                self._state.depth -= 1
            return

        connection = self._connection_factory()
        try:
            if hasattr(connection, "autocommit"):
                connection.autocommit = False
            self._state.connection = connection
            self._state.actor = actor
            self._state.depth = 1
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
            if int(getattr(self._state, "depth", 1)) != 1:
                raise ConflictError(
                    "database_transaction_depth_corrupt",
                    "Repository transaction depth did not return to its outer boundary.",
                )
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
            self._state.depth = 0
            connection.close()

    def reserve_idempotency(
        self,
        *,
        actor: ActorContext,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> CommandResponse | None:
        self._assert_current_actor(actor)
        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO idempotency_records (
                    institution_id, provider_id, operation, idempotency_key,
                    request_fingerprint, state, created_at, expires_at
                ) VALUES (%s, %s, %s, %s, %s, 'in_progress', %s, %s)
                ON CONFLICT (
                    institution_id, provider_id, operation, idempotency_key
                ) DO NOTHING
                RETURNING idempotency_key
                """,
                (
                    actor.institution_id,
                    actor.provider_id,
                    operation,
                    idempotency_key,
                    request_fingerprint,
                    created_at,
                    expires_at,
                ),
            )
            if cursor.fetchone() is not None:
                return None

            cursor.execute(
                """
                SELECT request_fingerprint, state, http_status,
                       response_headers, response_payload,
                       response_payload_hash, result_object_type,
                       result_object_id, result_version, audit_event_id,
                       expires_at
                FROM idempotency_records
                WHERE institution_id = %s
                  AND provider_id = %s
                  AND operation = %s
                  AND idempotency_key = %s
                FOR UPDATE
                """,
                (
                    actor.institution_id,
                    actor.provider_id,
                    operation,
                    idempotency_key,
                ),
            )
            row = cursor.fetchone()

        if row is None:
            raise ConflictError(
                "idempotency_reservation_missing",
                "The idempotency reservation could not be resolved safely.",
            )
        if row[0] != request_fingerprint:
            raise ConflictError(
                "idempotency_fingerprint_conflict",
                "The idempotency key was already used for a different request.",
            )
        if row[10] <= created_at:
            raise ConflictError(
                "idempotency_record_expired",
                "The idempotency record expired and must be purged before this key can be reused.",
            )
        if row[1] != "completed":
            raise ConflictError(
                "idempotency_command_in_progress",
                "The same idempotent command is already in progress.",
            )

        headers = _decoded_object(row[3], field="response_headers")
        body = _decoded_object(row[4], field="response_payload")
        expected_hash = sha256_json(body)
        if row[5] != expected_hash:
            raise ConflictError(
                "idempotency_payload_hash_mismatch",
                "The persisted idempotency response failed its integrity check.",
            )
        if headers.get("X-Response-Payload-Hash") != expected_hash:
            raise ConflictError(
                "idempotency_header_hash_mismatch",
                "The persisted idempotency response header does not match its body hash.",
            )
        if not all(isinstance(key, str) and isinstance(value, str) for key, value in headers.items()):
            raise ConflictError(
                "idempotency_headers_invalid",
                "Persisted response headers must contain string keys and values.",
            )

        return CommandResponse(
            status=int(row[2]),
            headers={str(key): str(value) for key, value in headers.items()},
            body=body,
            result_object_type=str(row[6]),
            result_object_id=str(row[7]),
            result_version=int(row[8]),
            audit_event_id=str(row[9]),
            replayed=True,
        )

    def complete_idempotency(
        self,
        *,
        actor: ActorContext,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        response: CommandResponse,
        completed_at: datetime,
    ) -> None:
        self._assert_current_actor(actor)
        body_hash = sha256_json(dict(response.body))
        if response.headers.get("X-Response-Payload-Hash") != body_hash:
            raise ConflictError(
                "idempotency_response_hash_missing",
                "The command response is missing its verified payload hash header.",
            )

        connection = self._connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE idempotency_records
                SET state = 'completed',
                    http_status = %s,
                    response_headers = %s::jsonb,
                    response_payload = %s::jsonb,
                    response_payload_hash = %s,
                    result_object_type = %s,
                    result_object_id = %s,
                    result_version = %s,
                    audit_event_id = %s,
                    completed_at = %s
                WHERE institution_id = %s
                  AND provider_id = %s
                  AND operation = %s
                  AND idempotency_key = %s
                  AND request_fingerprint = %s
                  AND state = 'in_progress'
                """,
                (
                    response.status,
                    _json_object(response.headers),
                    _json_object(response.body),
                    body_hash,
                    response.result_object_type,
                    response.result_object_id,
                    response.result_version,
                    response.audit_event_id,
                    completed_at,
                    actor.institution_id,
                    actor.provider_id,
                    operation,
                    idempotency_key,
                    request_fingerprint,
                ),
            )
            if cursor.rowcount != 1:
                raise ConflictError(
                    "idempotency_completion_conflict",
                    "The idempotency reservation was not completed exactly once.",
                )

    def _assert_current_actor(self, actor: ActorContext) -> None:
        current = self._actor()
        if (
            current.institution_id != actor.institution_id
            or current.provider_id != actor.provider_id
            or current.audit_scope != actor.audit_scope
        ):
            raise PermissionDenied(
                "idempotency_actor_scope_mismatch",
                "Idempotency access must use the current verified transaction actor.",
            )
