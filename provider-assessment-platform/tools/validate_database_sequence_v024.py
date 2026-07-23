#!/usr/bin/env python3
"""Validate the PostgreSQL 0.2.4 case-creation policy sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST = DATABASE / "MIGRATION_SEQUENCE.v0.2.4.json"


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
        require(manifest.get("sequence_version") == "0.2.4", "Unexpected sequence version")
        require(manifest.get("status") == "active-draft", "Sequence must remain active-draft")
        require(manifest.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must remain 15")
        require(manifest.get("supersedes_sequence") == "0.2.3", "Sequence must explicitly supersede 0.2.3")

        plan = manifest.get("execution_plan")
        require(isinstance(plan, list) and len(plan) == 9, "Execution plan must contain nine ordered steps")
        ordered = sorted(plan, key=lambda item: item.get("order", 0))
        require(
            [item.get("order") for item in ordered] == list(range(1, 10)),
            "Execution-plan order must be contiguous from 1 through 9",
        )
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
        ]
        actual = [(item.get("kind"), item.get("file")) for item in ordered]
        require(actual == expected, f"Unexpected execution plan: {actual}")

        for kind, file_name in expected:
            path = DATABASE / file_name
            require(path.is_file(), f"Execution-plan file is missing: {file_name}")
            if kind == "migration":
                validate_transaction(path)

        migration = validate_transaction(DATABASE / "postgresql.v0.2.4-case-creation-policy.sql")
        required_controls = (
            "DROP POLICY assigned_case_access ON cases",
            "CREATE POLICY assigned_case_select",
            "CREATE POLICY assigned_case_update",
            "CREATE POLICY assigned_case_delete",
            "CREATE POLICY case_insert_by_authenticated_creator",
            "created_by_provider_id = nullif(current_setting('app.provider_id', true), '')",
            "safety_screened_by_provider_id = nullif(current_setting('app.provider_id', true), '')",
            "status IN ('intake', 'safety_hold')",
            "current_pathway_id IS NULL",
            "current_pathway_version IS NULL",
        )
        for control in required_controls:
            require(control in migration, f"Case-creation migration is missing control: {control}")

        require(
            migration.count("CREATE POLICY assigned_case_") == 3,
            "Assigned access must be split into select, update, and delete policies",
        )
        require(
            "FOR INSERT" in migration and "version = 1" in migration,
            "Case creation policy must be insert-only and first-version-only",
        )
        require(
            "OR created_by_provider_id" not in migration,
            "Case creator must not receive permanent visibility merely by authorship",
        )

        smoke = read(DATABASE / "tests" / "case-creation-policy-smoke.sql")
        for evidence in (
            "A provider was allowed to create a case attributed to another provider",
            "A newly created unassigned case became visible before assignment",
            "Assigned case did not become visible after governed assignment",
            "NOBYPASSRLS",
        ):
            require(evidence in smoke, f"Case-creation smoke test lacks evidence: {evidence}")

        required_verification = set(manifest.get("required_verification", []))
        for requirement in (
            "postgresql_15_execution",
            "postgresql_16_execution",
            "authenticated_case_creator_policy_test",
            "post_creation_assignment_visibility_test",
            "cross_provider_attribution_rejection",
            "backup_restore_test",
        ):
            require(requirement in required_verification, f"Missing required verification: {requirement}")
    except ValidationFailure as exc:
        print(f"DATABASE 0.2.4 VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated PostgreSQL 0.2.4 execution plan, creator-only insert policy, and assignment-based visibility tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
