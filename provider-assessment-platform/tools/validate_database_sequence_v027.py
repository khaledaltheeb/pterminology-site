#!/usr/bin/env python3
"""Validate the PostgreSQL 0.2.7 least-function privilege sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST = DATABASE / "MIGRATION_SEQUENCE.v0.2.7.json"


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
        require(manifest.get("sequence_version") == "0.2.7", "Unexpected sequence version")
        require(manifest.get("status") == "active-draft", "Sequence must remain active-draft")
        require(manifest.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must remain 15")
        require(manifest.get("supersedes_sequence") == "0.2.6", "Sequence must explicitly supersede 0.2.6")

        plan = manifest.get("execution_plan")
        require(isinstance(plan, list) and len(plan) == 16, "Execution plan must contain sixteen ordered steps")
        ordered = sorted(plan, key=lambda item: item.get("order", 0))
        require([item.get("order") for item in ordered] == list(range(1, 17)), "Execution-plan order must be contiguous")
        expected_tail = [
            ("migration", "postgresql.v0.2.6-audit-tip-resolution.sql"),
            ("test", "tests/audit-tip-resolution-smoke.sql"),
            ("test", "tests/audit-cycle-resolution-smoke.sql"),
            ("migration", "postgresql.v0.2.7-function-privileges.sql"),
            ("test", "tests/function-privilege-smoke.sql"),
        ]
        actual_tail = [(item.get("kind"), item.get("file")) for item in ordered[-5:]]
        require(actual_tail == expected_tail, f"Unexpected sequence tail: {actual_tail}")

        for item in ordered:
            file_name = item.get("file")
            require(isinstance(file_name, str), "Execution-plan file name is invalid")
            path = DATABASE / file_name
            require(path.is_file(), f"Execution-plan file is missing: {file_name}")
            if item.get("kind") == "migration":
                validate_transaction(path)

        migration = validate_transaction(DATABASE / "postgresql.v0.2.7-function-privileges.sql")
        internal_functions = (
            "deny_immutable_mutation()",
            "set_case_update_metadata()",
            "enforce_case_safety_hold()",
            "enforce_review_version_chain()",
            "enforce_assessment_plan_version_chain()",
            "enforce_approved_team_review_for_report()",
            "enforce_audit_event_chain()",
            "institution_audit_chain_tip(text)",
        )
        for signature in internal_functions:
            require(
                f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC" in migration,
                f"Internal function remains public in migration: {signature}",
            )
        require(
            "REVOKE ALL ON FUNCTION current_institution_last_audit_hash() FROM PUBLIC" in migration,
            "Application-facing audit hash function must also lose PUBLIC execution",
        )
        require("GRANT " not in migration.upper(), "Deployment-role grants must not be hard-coded in the schema migration")

        smoke = read(DATABASE / "tests" / "function-privilege-smoke.sql")
        for evidence in (
            "Internal institution-argument audit helper remained executable",
            "Internal audit trigger function remained executable",
            "Internal safety trigger function remained executable",
            "Internal institution-argument audit helper was callable by the service-like role",
            "Revoked direct trigger execution prevented governed trigger behavior",
            "GRANT EXECUTE ON FUNCTION current_institution_last_audit_hash() TO pa_function_test",
            "NOBYPASSRLS",
        ):
            require(evidence in smoke, f"Function-privilege smoke test lacks evidence: {evidence}")
        require(
            "GRANT EXECUTE ON ALL FUNCTIONS" not in smoke,
            "Function privilege smoke test must not use blanket execution grants",
        )

        setup = read(DATABASE / "tests" / "service-integration-setup.sql")
        require(
            "GRANT EXECUTE ON FUNCTION current_institution_last_audit_hash() TO pa_service_app" in setup,
            "Service integration role must receive the one application-facing function explicitly",
        )
        require(
            "GRANT EXECUTE ON ALL FUNCTIONS" not in setup,
            "Service integration role must not receive blanket function execution",
        )

        required_verification = set(manifest.get("required_verification", []))
        for requirement in (
            "postgresql_15_execution",
            "postgresql_16_execution",
            "public_function_revocation_test",
            "explicit_service_function_grant_test",
            "trigger_execution_without_direct_execute_test",
            "independent_database_security_review",
            "backup_restore_test",
        ):
            require(requirement in required_verification, f"Missing required verification: {requirement}")
    except ValidationFailure as exc:
        print(f"DATABASE 0.2.7 VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated PostgreSQL 0.2.7 least-function privilege, explicit service grant, and trigger behavior without direct execution rights.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
