#!/usr/bin/env python3
"""Validate the PostgreSQL 0.2.8 transactional idempotency sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST = DATABASE / "MIGRATION_SEQUENCE.v0.2.8.json"


class ValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def read(path: Path) -> str:
    require(path.is_file(), f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read(path))
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"Invalid JSON in {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def validate_transaction(path: Path) -> str:
    sql = read(path)
    require(sql.lstrip().startswith("BEGIN;"), f"{path.name} must begin with BEGIN")
    require(sql.rstrip().endswith("COMMIT;"), f"{path.name} must end with COMMIT")
    upper = sql.upper()
    for token in ("BYPASSRLS", "DROP TABLE", "DROP SCHEMA", "TRUNCATE "):
        require(token not in upper, f"{path.name} contains prohibited SQL: {token.strip()}")
    return sql


def main() -> int:
    try:
        manifest = load(MANIFEST)
        require(manifest.get("sequence_version") == "0.2.8", "Unexpected sequence version")
        require(manifest.get("status") == "active-draft", "Sequence must remain active-draft")
        require(manifest.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must remain 15")
        require(manifest.get("supersedes_sequence") == "0.2.7", "Sequence must explicitly supersede 0.2.7")

        plan = manifest.get("execution_plan")
        require(isinstance(plan, list) and len(plan) == 18, "Execution plan must contain eighteen ordered steps")
        ordered = sorted(plan, key=lambda item: item.get("order", 0))
        require([item.get("order") for item in ordered] == list(range(1, 19)), "Execution-plan order must be contiguous")
        require(
            [(item.get("kind"), item.get("file")) for item in ordered[-4:]]
            == [
                ("migration", "postgresql.v0.2.7-function-privileges.sql"),
                ("test", "tests/function-privilege-smoke.sql"),
                ("migration", "postgresql.v0.2.8-idempotency.sql"),
                ("test", "tests/idempotency-ledger-smoke.sql"),
            ],
            "Unexpected 0.2.8 execution-plan tail",
        )

        for item in ordered:
            file_name = item.get("file")
            require(isinstance(file_name, str), "Execution-plan file name is invalid")
            path = DATABASE / file_name
            require(path.is_file(), f"Execution-plan file is missing: {file_name}")
            if item.get("kind") == "migration":
                validate_transaction(path)

        migration = validate_transaction(DATABASE / "postgresql.v0.2.8-idempotency.sql")
        required_controls = (
            "CREATE TABLE idempotency_records",
            "PRIMARY KEY (\n        institution_id,\n        provider_id,\n        operation,\n        idempotency_key",
            "request_fingerprint ~ '^[a-f0-9]{64}$'",
            "state text NOT NULL CHECK (state IN ('in_progress', 'completed'))",
            "pg_column_size(response_payload) <= 65536",
            "FOREIGN KEY (audit_event_id, institution_id)",
            "CREATE OR REPLACE FUNCTION enforce_idempotency_record_transition()",
            "only in_progress to completed transition is allowed",
            "ALTER TABLE idempotency_records FORCE ROW LEVEL SECURITY",
            "CREATE POLICY idempotency_provider_scope",
            "CREATE OR REPLACE FUNCTION purge_expired_idempotency_records",
            "FOR UPDATE SKIP LOCKED",
            "REVOKE ALL ON FUNCTION purge_expired_idempotency_records(integer) FROM PUBLIC",
        )
        for control in required_controls:
            require(control in migration, f"Idempotency migration is missing control: {control}")

        require(
            "provider_id = nullif(current_setting('app.provider_id', true), '')" in migration,
            "Idempotency records must be provider scoped under RLS",
        )
        require(
            "current_user = (\n        SELECT pg_get_userbyid(relowner)" in migration,
            "Owner-executed bounded cleanup must be explicit in RLS",
        )
        require(
            "GRANT " not in migration.upper(),
            "Deployment-role grants must not be hard-coded in the idempotency migration",
        )
        require(
            "identity_vault_reference" not in migration
            and "date_of_birth" not in migration
            and "test_item" not in migration,
            "Idempotency ledger must not define direct identity or protected assessment columns",
        )

        smoke = read(DATABASE / "tests" / "idempotency-ledger-smoke.sql")
        for evidence in (
            "Same scoped idempotency key accepted a different request fingerprint",
            "A different provider could see another provider idempotency record",
            "A completed idempotency record remained mutable",
            "The service-like role could delete an idempotency record directly",
            "Expected one expired idempotency record to be purged",
            "Non-expired completed idempotency record was incorrectly purged",
            "NOBYPASSRLS",
        ):
            require(evidence in smoke, f"Idempotency smoke test lacks evidence: {evidence}")
        require(
            "GRANT DELETE ON idempotency_records" not in smoke,
            "Service-like idempotency role must not receive direct DELETE",
        )
        require(
            "GRANT EXECUTE ON FUNCTION purge_expired_idempotency_records(integer) TO pa_idempotency_maintenance" in smoke,
            "Maintenance purge must use one explicit function grant",
        )

        setup = read(DATABASE / "tests" / "service-integration-setup.sql")
        require(
            "DELETE" not in setup.split("TO pa_service_app", 1)[0],
            "Service integration grants must not include DELETE",
        )
        require(
            "purge_expired_idempotency_records" not in setup,
            "Service role must never receive idempotency purge execution",
        )

        required_verification = set(manifest.get("required_verification", []))
        for requirement in (
            "postgresql_15_execution",
            "postgresql_16_execution",
            "provider_scoped_idempotency_test",
            "request_fingerprint_conflict_test",
            "completed_idempotency_immutability_test",
            "bounded_response_snapshot_test",
            "governed_expired_record_purge_test",
            "service_role_no_direct_delete_test",
            "backup_restore_test",
        ):
            require(requirement in required_verification, f"Missing required verification: {requirement}")
    except ValidationFailure as exc:
        print(f"DATABASE 0.2.8 VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated PostgreSQL 0.2.8 provider-scoped idempotency, immutable replay snapshots, and governed bounded retention cleanup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
