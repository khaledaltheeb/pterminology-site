"""Durable idempotent command execution across the service transaction boundary."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol, TypeVar

from .domain import ActorContext
from .errors import ValidationError


T = TypeVar("T")
_KEY = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")
_OPERATION = re.compile(r"^[a-z][a-z0-9_.:-]{2,120}$")


def _immutable_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


def canonical_json_bytes(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "idempotency_request_not_canonicalizable",
            "The request payload cannot be converted to canonical JSON.",
        ) from exc
    return encoded.encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class CommandResponse:
    status: int
    headers: Mapping[str, str]
    body: Mapping[str, Any]
    result_object_type: str
    result_object_id: str
    result_version: int
    audit_event_id: str
    replayed: bool = False

    def __post_init__(self) -> None:
        if not 200 <= self.status <= 299:
            raise ValueError("Only successful command responses may be persisted")
        if self.result_version < 1:
            raise ValueError("Result version must be positive")
        if not self.result_object_type.strip() or not self.result_object_id.strip():
            raise ValueError("Result object type and identifier are required")
        if not self.audit_event_id.strip():
            raise ValueError("Audit event identifier is required")
        object.__setattr__(self, "headers", _immutable_mapping(self.headers))
        object.__setattr__(self, "body", _immutable_mapping(self.body))


class DurableIdempotencyRepository(Protocol):
    def atomic(self, *, actor: ActorContext): ...

    def reserve_idempotency(
        self,
        *,
        actor: ActorContext,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        created_at: datetime,
        expires_at: datetime,
    ) -> CommandResponse | None: ...

    def complete_idempotency(
        self,
        *,
        actor: ActorContext,
        operation: str,
        idempotency_key: str,
        request_fingerprint: str,
        response: CommandResponse,
        completed_at: datetime,
    ) -> None: ...


class DurableCommandExecutor:
    """Execute and persist one response in the same repository transaction."""

    def __init__(
        self,
        repository: DurableIdempotencyRepository,
        *,
        retention: timedelta = timedelta(hours=24),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if retention <= timedelta(minutes=1) or retention > timedelta(days=7):
            raise ValueError("Idempotency retention must be over one minute and at most seven days")
        self._repository = repository
        self._retention = retention
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def execute(
        self,
        *,
        actor: ActorContext,
        operation: str,
        idempotency_key: str,
        request_payload: Any,
        command: Callable[[], CommandResponse],
    ) -> CommandResponse:
        if not _OPERATION.fullmatch(operation):
            raise ValidationError(
                "invalid_idempotency_operation",
                "Idempotency operation identifier is invalid.",
            )
        if not _KEY.fullmatch(idempotency_key):
            raise ValidationError(
                "invalid_idempotency_key",
                "Idempotency key must contain 16 to 128 safe characters.",
            )
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("Idempotency clock must return a timezone-aware datetime")
        fingerprint = sha256_json(request_payload)

        with self._repository.atomic(actor=actor):
            replay = self._repository.reserve_idempotency(
                actor=actor,
                operation=operation,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                created_at=now,
                expires_at=now + self._retention,
            )
            if replay is not None:
                return replace(replay, replayed=True)

            response = command()
            response_hash = sha256_json(
                {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": dict(response.body),
                    "result_object_type": response.result_object_type,
                    "result_object_id": response.result_object_id,
                    "result_version": response.result_version,
                    "audit_event_id": response.audit_event_id,
                }
            )
            enriched_headers = dict(response.headers)
            enriched_headers.setdefault("X-Response-Payload-Hash", response_hash)
            persisted = replace(response, headers=enriched_headers)
            self._repository.complete_idempotency(
                actor=actor,
                operation=operation,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                response=persisted,
                completed_at=self._clock(),
            )
            return persisted
