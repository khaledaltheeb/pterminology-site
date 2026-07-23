#!/usr/bin/env python3
"""Validate the PostgreSQL 0.2.6 link-derived audit sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST = DATABASE / "MIGRATION_SEQUENCE.v0.2.6.json"


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
        require(manifest.get("sequence_version") == "0.2.6", "Unexpected sequence version")
        require(manifest.get("status") == "active-draft", "Sequence must remain active-draft")
        require(manifest.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must remain 15")
        require(manifest.get("supersedes_sequence") == "0.2.5", "Sequence must explicitly supersede 0.2.5")

        plan = manifest.get("execution_plan")
        require(isinstance(plan, list) and len(plan) == 14, "Execution plan must contain fourteen ordered steps")
        ordered = sorted(plan, key=lambda item: item.get("order", 0))
        require([item.get("order") for item in ordered] == list(range(1, 15)), "Execution-plan order must be contiguous")
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
            ("migration", "postgresql.v0.2.6-audit-tip-resolution.sql"),
            ("test", "tests/audit-tip-resolution-smoke.sql"),
            ("test", "tests/audit-cycle-resolution-smoke.sql"),
        ]
        actual = [(item.get("kind"), item.get("file")) for item in ordered]
        require(actual == expected, f"Unexpected execution plan: {actual}")

        for kind, file_name in expected:
            path = DATABASE / file_name
            require(path.is_file(), f"Execution-plan file is missing: {file_name}")
            if kind == "migration":
                validate_transaction(path)

        migration = validate_transaction(DATABASE / "postgresql.v0.2.6-audit-tip-resolution.sql")
        required_controls = (
            "CREATE OR REPLACE FUNCTION institution_audit_chain_tip(target_institution text)",
            "SELECT count(*)\n    INTO event_count",
            "NOT EXISTS (",
            "child.previous_event_hash = parent.event_hash",
            "IF event_count = 0 THEN",
            "IF tip_count <> 1 THEN",
            "audit chain must have exactly one terminal event",
            "RETURN institution_audit_chain_tip(current_institution)",
            "expected_previous_hash := institution_audit_chain_tip(NEW.institution_id)",
            "pg_advisory_xact_lock(hashtextextended",
        )
        for control in required_controls:
            require(control in migration, f"Audit-tip migration is missing control: {control}")

        prohibited_ordering = (
            "ORDER BY occurred_at",
            "ORDER BY audit_event_id",
            "max(occurred_at",
        )
        for token in prohibited_ordering:
            require(token not in migration, f"Audit tip must not depend on mutable chronology: {token}")

        tip_smoke = read(DATABASE / "tests" / "audit-tip-resolution-smoke.sql")
        for evidence in (
            "Audit tip was resolved by timestamp instead of hash links",
            "A pre-existing audit-chain fork was not detected",
            "2001-01-01 00:00:00+00",
            "NOBYPASSRLS",
            "DISABLE TRIGGER audit_events_chain_guard",
            "ENABLE TRIGGER audit_events_chain_guard",
        ):
            require(evidence in tip_smoke, f"Audit-tip smoke test lacks evidence: {evidence}")

        cycle_smoke = read(DATABASE / "tests" / "audit-cycle-resolution-smoke.sql")
        for evidence in (
            "A closed audit-chain cycle with zero terminal events was not detected",
            "repeat('5', 64)",
            "repeat('4', 64)",
            "DISABLE TRIGGER audit_events_chain_guard",
            "ENABLE TRIGGER audit_events_chain_guard",
        ):
            require(evidence in cycle_smoke, f"Audit-cycle smoke test lacks evidence: {evidence}")

        required_verification = set(manifest.get("required_verification", []))
        for requirement in (
            "postgresql_15_execution",
            "postgresql_16_execution",
            "link_derived_audit_tip_test",
            "out_of_order_timestamp_test",
            "historical_audit_fork_detection_test",
            "closed_audit_cycle_detection_test",
            "institution_audit_serialization_lock",
            "backup_restore_test",
        ):
            require(requirement in required_verification, f"Missing required verification: {requirement}")
    except ValidationFailure as exc:
        print(f"DATABASE 0.2.6 VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated PostgreSQL 0.2.6 link-derived audit tip, out-of-order time handling, fork and cycle detection, and locked appends.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
