"""Scoped idempotency boundary for write commands.

The executor stores only a caller-supplied SHA-256 request fingerprint and a
synthetic result object. Production adapters must persist an opaque response
reference, not protected assessment payloads or direct identity data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Callable, Generic, TypeVar

from .errors import ConflictError, ValidationError


T = TypeVar("T")
_HASH = re.compile(r"^[a-f0-9]{64}$")
_KEY = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValidationError(
            "timezone_required",
            "Idempotency timestamps must be timezone-aware.",
        )
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class IdempotencyScope:
    institution_id: str
    provider_id: str
    operation: str

    def key(self, idempotency_key: str) -> tuple[str, str, str, str]:
        return (
            self.institution_id,
            self.provider_id,
            self.operation,
            idempotency_key,
        )


@dataclass(slots=True)
class _Entry(Generic[T]):
    request_fingerprint: str
    state: str
    result: T | None
    created_at: datetime
    expires_at: datetime


class IdempotentCommandExecutor:
    """Thread-safe fail-closed executor for one idempotency namespace."""

    def __init__(self, *, retention: timedelta = timedelta(hours=24)) -> None:
        if retention <= timedelta(0):
            raise ValueError("Idempotency retention must be positive")
        self._retention = retention
        self._lock = RLock()
        self._entries: dict[tuple[str, str, str, str], _Entry[object]] = {}

    def execute(
        self,
        *,
        scope: IdempotencyScope,
        idempotency_key: str,
        request_fingerprint: str,
        now: datetime,
        command: Callable[[], T],
    ) -> T:
        current = _utc(now)
        self._validate_scope(scope)
        if not _KEY.fullmatch(idempotency_key):
            raise ValidationError(
                "invalid_idempotency_key",
                "Idempotency key format or length is invalid.",
            )
        if not _HASH.fullmatch(request_fingerprint):
            raise ValidationError(
                "invalid_request_fingerprint",
                "Request fingerprint must be a lowercase SHA-256 digest.",
            )

        storage_key = scope.key(idempotency_key)
        with self._lock:
            self._purge_expired(current)
            entry = self._entries.get(storage_key)
            if entry is not None:
                if entry.request_fingerprint != request_fingerprint:
                    raise ConflictError(
                        "idempotency_payload_mismatch",
                        "The idempotency key was already used for a different request fingerprint.",
                    )
                if entry.state == "completed":
                    return entry.result  # type: ignore[return-value]
                raise ConflictError(
                    "idempotency_request_in_progress",
                    "An equivalent write command is already in progress.",
                )

            self._entries[storage_key] = _Entry(
                request_fingerprint=request_fingerprint,
                state="in_progress",
                result=None,
                created_at=current,
                expires_at=current + self._retention,
            )

        try:
            result = command()
        except BaseException:
            with self._lock:
                current_entry = self._entries.get(storage_key)
                if (
                    current_entry is not None
                    and current_entry.state == "in_progress"
                    and current_entry.request_fingerprint == request_fingerprint
                ):
                    del self._entries[storage_key]
            raise

        with self._lock:
            entry = self._entries.get(storage_key)
            if entry is None or entry.request_fingerprint != request_fingerprint:
                raise ConflictError(
                    "idempotency_reservation_lost",
                    "The idempotency reservation changed before command completion.",
                )
            entry.state = "completed"
            entry.result = result
            entry.expires_at = current + self._retention
        return result

    def size(self, *, now: datetime) -> int:
        current = _utc(now)
        with self._lock:
            self._purge_expired(current)
            return len(self._entries)

    def _purge_expired(self, now: datetime) -> None:
        expired = [
            key
            for key, value in self._entries.items()
            if value.expires_at <= now and value.state != "in_progress"
        ]
        for key in expired:
            del self._entries[key]

    @staticmethod
    def _validate_scope(scope: IdempotencyScope) -> None:
        for field, value in (
            ("institution_id", scope.institution_id),
            ("provider_id", scope.provider_id),
            ("operation", scope.operation),
        ):
            if not value.strip() or len(value) > 128:
                raise ValidationError(
                    "invalid_idempotency_scope",
                    "Idempotency scope is incomplete or too long.",
                    {"field": field},
                )
