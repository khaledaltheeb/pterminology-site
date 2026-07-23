from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from service.provider_assessment import (
    ConflictError,
    IdempotencyScope,
    IdempotentCommandExecutor,
    ValidationError,
)


NOW = datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc)
SCOPE = IdempotencyScope(
    institution_id="INST-TEST01",
    provider_id="PROV-TEST01",
    operation="case.create",
)


class IdempotentCommandExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.executor = IdempotentCommandExecutor(retention=timedelta(hours=1))

    def test_completed_replay_returns_cached_result_without_second_execution(self) -> None:
        calls = 0

        def command():
            nonlocal calls
            calls += 1
            return {"case_id": "CASE-000001"}

        first = self.executor.execute(
            scope=SCOPE,
            idempotency_key="REQUEST-KEY-000001",
            request_fingerprint="a" * 64,
            now=NOW,
            command=command,
        )
        second = self.executor.execute(
            scope=SCOPE,
            idempotency_key="REQUEST-KEY-000001",
            request_fingerprint="a" * 64,
            now=NOW + timedelta(minutes=1),
            command=command,
        )

        self.assertIs(first, second)
        self.assertEqual(calls, 1)

    def test_same_key_with_different_fingerprint_is_rejected(self) -> None:
        self.executor.execute(
            scope=SCOPE,
            idempotency_key="REQUEST-KEY-000002",
            request_fingerprint="b" * 64,
            now=NOW,
            command=lambda: "created",
        )

        with self.assertRaises(ConflictError) as raised:
            self.executor.execute(
                scope=SCOPE,
                idempotency_key="REQUEST-KEY-000002",
                request_fingerprint="c" * 64,
                now=NOW,
                command=lambda: "must-not-run",
            )
        self.assertEqual(raised.exception.code, "idempotency_payload_mismatch")

    def test_failed_command_releases_reservation_for_retry(self) -> None:
        attempts = 0

        def command():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("synthetic failure")
            return "success"

        with self.assertRaises(RuntimeError):
            self.executor.execute(
                scope=SCOPE,
                idempotency_key="REQUEST-KEY-000003",
                request_fingerprint="d" * 64,
                now=NOW,
                command=command,
            )

        result = self.executor.execute(
            scope=SCOPE,
            idempotency_key="REQUEST-KEY-000003",
            request_fingerprint="d" * 64,
            now=NOW + timedelta(seconds=1),
            command=command,
        )
        self.assertEqual(result, "success")
        self.assertEqual(attempts, 2)

    def test_same_key_isolated_by_provider_and_operation(self) -> None:
        key = "REQUEST-KEY-000004"
        first = self.executor.execute(
            scope=SCOPE,
            idempotency_key=key,
            request_fingerprint="e" * 64,
            now=NOW,
            command=lambda: "case-result",
        )
        second = self.executor.execute(
            scope=IdempotencyScope(
                institution_id="INST-TEST01",
                provider_id="PROV-TEST02",
                operation="case.create",
            ),
            idempotency_key=key,
            request_fingerprint="f" * 64,
            now=NOW,
            command=lambda: "other-provider-result",
        )
        third = self.executor.execute(
            scope=IdempotencyScope(
                institution_id="INST-TEST01",
                provider_id="PROV-TEST01",
                operation="safety_event.create",
            ),
            idempotency_key=key,
            request_fingerprint="1" * 64,
            now=NOW,
            command=lambda: "other-operation-result",
        )

        self.assertEqual(
            (first, second, third),
            ("case-result", "other-provider-result", "other-operation-result"),
        )

    def test_completed_entry_expires_after_retention(self) -> None:
        calls = 0

        def command():
            nonlocal calls
            calls += 1
            return calls

        first = self.executor.execute(
            scope=SCOPE,
            idempotency_key="REQUEST-KEY-000005",
            request_fingerprint="2" * 64,
            now=NOW,
            command=command,
        )
        second = self.executor.execute(
            scope=SCOPE,
            idempotency_key="REQUEST-KEY-000005",
            request_fingerprint="2" * 64,
            now=NOW + timedelta(hours=2),
            command=command,
        )
        self.assertEqual((first, second), (1, 2))

    def test_invalid_key_or_fingerprint_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            self.executor.execute(
                scope=SCOPE,
                idempotency_key="short",
                request_fingerprint="3" * 64,
                now=NOW,
                command=lambda: None,
            )
        with self.assertRaises(ValidationError):
            self.executor.execute(
                scope=SCOPE,
                idempotency_key="REQUEST-KEY-000006",
                request_fingerprint="not-a-hash",
                now=NOW,
                command=lambda: None,
            )


if __name__ == "__main__":
    unittest.main()
