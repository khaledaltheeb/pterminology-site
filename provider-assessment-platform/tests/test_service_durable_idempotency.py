from __future__ import annotations

import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone

from service.provider_assessment import (
    ActorContext,
    CommandResponse,
    ConflictError,
    DurableCommandExecutor,
    ValidationError,
)


NOW = datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc)


@dataclass
class Record:
    fingerprint: str
    response: CommandResponse | None
    expires_at: datetime


class FakeDurableRepository:
    def __init__(self) -> None:
        self.records: dict[tuple[str, str, str, str], Record] = {}
        self.depth = 0

    @contextmanager
    def atomic(self, *, actor: ActorContext):
        del actor
        outer = self.depth == 0
        snapshot = dict(self.records) if outer else None
        self.depth += 1
        try:
            yield
        except BaseException:
            if outer and snapshot is not None:
                self.records = snapshot
            raise
        finally:
            self.depth -= 1

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
        del created_at
        key = (
            actor.institution_id,
            actor.provider_id,
            operation,
            idempotency_key,
        )
        existing = self.records.get(key)
        if existing is None:
            self.records[key] = Record(request_fingerprint, None, expires_at)
            return None
        if existing.fingerprint != request_fingerprint:
            raise ConflictError(
                "idempotency_fingerprint_conflict",
                "The key was used for a different request.",
            )
        if existing.response is None:
            raise ConflictError(
                "idempotency_command_in_progress",
                "The command is already in progress.",
            )
        return existing.response

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
        del completed_at
        key = (
            actor.institution_id,
            actor.provider_id,
            operation,
            idempotency_key,
        )
        existing = self.records.get(key)
        if existing is None or existing.fingerprint != request_fingerprint:
            raise ConflictError(
                "idempotency_completion_conflict",
                "Reservation is missing or changed.",
            )
        if existing.response is not None:
            raise ConflictError(
                "idempotency_completion_conflict",
                "Reservation was already completed.",
            )
        existing.response = response


class DurableCommandExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = FakeDurableRepository()
        self.executor = DurableCommandExecutor(
            self.repository,
            clock=lambda: NOW,
        )
        self.actor = ActorContext(
            provider_id="PROV-TEST01",
            institution_id="INST-TEST01",
            roles=frozenset({"provider"}),
            active=True,
            professional_license_verified=True,
            professional_license_reference="LICENSE:TEST:0001",
        )

    @staticmethod
    def response() -> CommandResponse:
        return CommandResponse(
            status=201,
            headers={
                "ETag": 'W/"case-version-1"',
                "X-Audit-Event-Id": "AUD-00000001",
            },
            body={"case_id": "CASE-00000001", "version": 1},
            result_object_type="case",
            result_object_id="CASE-00000001",
            result_version=1,
            audit_event_id="AUD-00000001",
        )

    def test_replay_returns_exact_response_without_second_execution(self) -> None:
        calls = 0

        def command() -> CommandResponse:
            nonlocal calls
            calls += 1
            return self.response()

        first = self.executor.execute(
            actor=self.actor,
            operation="case.create",
            idempotency_key="IDEMPOTENCY-UNIT-0001",
            request_payload={"value": 1},
            command=command,
        )
        replay = self.executor.execute(
            actor=self.actor,
            operation="case.create",
            idempotency_key="IDEMPOTENCY-UNIT-0001",
            request_payload={"value": 1},
            command=command,
        )

        self.assertEqual(calls, 1)
        self.assertFalse(first.replayed)
        self.assertTrue(replay.replayed)
        self.assertEqual(dict(first.body), dict(replay.body))
        self.assertEqual(dict(first.headers), dict(replay.headers))
        self.assertEqual(
            first.headers["X-Response-Payload-Hash"],
            replay.headers["X-Response-Payload-Hash"],
        )

    def test_same_key_with_different_payload_is_rejected(self) -> None:
        self.executor.execute(
            actor=self.actor,
            operation="case.create",
            idempotency_key="IDEMPOTENCY-UNIT-0002",
            request_payload={"value": 1},
            command=self.response,
        )
        with self.assertRaises(ConflictError) as raised:
            self.executor.execute(
                actor=self.actor,
                operation="case.create",
                idempotency_key="IDEMPOTENCY-UNIT-0002",
                request_payload={"value": 2},
                command=self.response,
            )
        self.assertEqual(raised.exception.code, "idempotency_fingerprint_conflict")

    def test_failed_command_rolls_back_reservation_and_can_retry(self) -> None:
        attempts = 0

        def fail() -> CommandResponse:
            nonlocal attempts
            attempts += 1
            raise ConflictError("synthetic_failure", "Synthetic failure")

        with self.assertRaises(ConflictError):
            self.executor.execute(
                actor=self.actor,
                operation="case.create",
                idempotency_key="IDEMPOTENCY-UNIT-0003",
                request_payload={"value": 3},
                command=fail,
            )
        self.assertEqual(self.repository.records, {})

        result = self.executor.execute(
            actor=self.actor,
            operation="case.create",
            idempotency_key="IDEMPOTENCY-UNIT-0003",
            request_payload={"value": 3},
            command=self.response,
        )
        self.assertFalse(result.replayed)
        self.assertEqual(attempts, 1)

    def test_invalid_key_and_noncanonical_payload_are_rejected(self) -> None:
        with self.assertRaises(ValidationError) as short_key:
            self.executor.execute(
                actor=self.actor,
                operation="case.create",
                idempotency_key="short",
                request_payload={},
                command=self.response,
            )
        self.assertEqual(short_key.exception.code, "invalid_idempotency_key")

        with self.assertRaises(ValidationError) as noncanonical:
            self.executor.execute(
                actor=self.actor,
                operation="case.create",
                idempotency_key="IDEMPOTENCY-UNIT-0004",
                request_payload={"unsupported": {1, 2}},
                command=self.response,
            )
        self.assertEqual(
            noncanonical.exception.code,
            "idempotency_request_not_canonicalizable",
        )


if __name__ == "__main__":
    unittest.main()
