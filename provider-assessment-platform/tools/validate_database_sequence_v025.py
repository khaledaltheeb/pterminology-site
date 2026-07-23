#!/usr/bin/env python3
"""Validate the PostgreSQL 0.2.5 safety and audit consistency sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST = DATABASE / "MIGRATION_SEQUENCE.v0.2.5.json"


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
        require(manifest.get("sequence_version") == "0.2.5", "Unexpected sequence version")
        require(manifest.get("status") == "active-draft", "Sequence must remain active-draft")
        require(manifest.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must remain 15")
        require(manifest.get("supersedes_sequence") == "0.2.4", "Sequence must explicitly supersede 0.2.4")

        plan = manifest.get("execution_plan")
        require(isinstance(plan, list) and len(plan) == 11, "Execution plan must contain eleven ordered steps")
        ordered = sorted(plan, key=lambda item: item.get("order", 0))
        require([item.get("order") for item in ordered] == list(range(1, 12)), "Execution-plan order must be contiguous")
        expected = [
            ("migration", "postgresql.v0.2.0.sql"),
            ("migration", "postgresql.v0.2.2-review-versioning.sql"),
            ("test", "tests/rls-smoke-v2.sql"),
            ("test", "tests/review-versioning-smoke.sql"),
            ("fixture", "tests/intake-alignment-legacy-seed.sql"),
            ("migration", "postgresql.v0.2.3-intake-alignment.sql"),
            ("test", "tests/intake-alignment-backfill-check.sql"),
            ("migration", "postgresql.v0.2.4-case-creation-policy.sql"),
            ("test", "tests/case-creation-policy-smoke.sql"),
            ("migration", "postgresql.v0.2.5-safety-audit-consistency.sql"),
            ("test", "tests/safety-audit-consistency-smoke.sql"),
        ]
        actual = [(item.get("kind"), item.get("file")) for item in ordered]
        require(actual == expected, f"Unexpected execution plan: {actual}")

        for kind, file_name in expected:
            path = DATABASE / file_name
            require(path.is_file(), f"Execution-plan file is missing: {file_name}")
            if kind == "migration":
                validate_transaction(path)

        migration = validate_transaction(DATABASE / "postgresql.v0.2.5-safety-audit-consistency.sql")
        required_controls = (
            "safety_level IS DISTINCT FROM NEW.level",
            "status IS DISTINCT FROM 'safety_hold'",
            "AND safety_level = 'none_identified'",
            "CREATE OR REPLACE FUNCTION current_institution_last_audit_hash()",
            "CREATE OR REPLACE FUNCTION enforce_audit_event_chain()",
            "SECURITY DEFINER",
            "pg_advisory_xact_lock(hashtextextended",
            "NEW.previous_event_hash IS DISTINCT FROM expected_previous_hash",
            "CREATE TRIGGER audit_events_chain_guard",
        )
        for control in required_controls:
            require(control in migration, f"Safety-audit migration is missing control: {control}")

        require(
            migration.count("pg_advisory_xact_lock(hashtextextended") >= 2,
            "Both terminal-hash reads and audit inserts must use the institution advisory lock",
        )
        require(
            "UPDATE cases\n        SET safety_level = 'monitor'" in migration,
            "Monitor fallback update is missing",
        )
        require(
            "OR status IS DISTINCT FROM 'safety_hold'" in migration,
            "Urgent safety trigger must become idempotent after service-first update",
        )

        smoke = read(DATABASE / "tests" / "safety-audit-consistency-smoke.sql")
        for evidence in (
            "Idempotent safety trigger raised case version twice",
            "Monitor event downgraded urgent safety state",
            "Stale audit predecessor was not rejected",
            "Terminal audit hash did not advance",
            "NOBYPASSRLS",
        ):
            require(evidence in smoke, f"Safety-audit smoke test lacks evidence: {evidence}")

        required_verification = set(manifest.get("required_verification", []))
        for requirement in (
            "postgresql_15_execution",
            "postgresql_16_execution",
            "idempotent_safety_trigger_test",
            "urgent_state_non_downgrade_test",
            "database_audit_chain_conflict_test",
            "institution_audit_serialization_lock",
            "backup_restore_test",
        ):
            require(requirement in required_verification, f"Missing required verification: {requirement}")
    except ValidationFailure as exc:
        print(f"DATABASE 0.2.5 VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated PostgreSQL 0.2.5 safety idempotence, urgent-state non-downgrade, and database-enforced audit chain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
