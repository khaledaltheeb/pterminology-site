#!/usr/bin/env python3
"""Validate the active PostgreSQL 0.2.1 sequence and review-versioning controls."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
SEQUENCE = DATABASE / "MIGRATION_SEQUENCE.v0.2.1.json"


class SequenceFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SequenceFailure(message)


def read(path: Path) -> str:
    require(path.is_file(), f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(read(path))
    except json.JSONDecodeError as exc:
        raise SequenceFailure(f"Invalid JSON in {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def validate_transaction(path: Path, sql: str) -> None:
    require(sql.lstrip().startswith("BEGIN;"), f"{path.name} must begin with BEGIN")
    require(sql.rstrip().endswith("COMMIT;"), f"{path.name} must end with COMMIT")
    upper = sql.upper()
    for token in (
        "DISABLE ROW LEVEL SECURITY",
        "BYPASSRLS",
        "DROP TABLE",
        "DROP SCHEMA",
        "TRUNCATE ",
    ):
        require(token not in upper, f"{path.name} contains prohibited SQL: {token.strip()}")


def main() -> int:
    try:
        sequence = load(SEQUENCE)
        require(sequence.get("sequence_version") == "0.2.1", "Unexpected sequence version")
        require(sequence.get("status") == "active-draft", "Sequence must remain active-draft")
        require(sequence.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(sequence.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must be 15")

        ordered_files = sequence.get("ordered_files")
        require(isinstance(ordered_files, list) and len(ordered_files) == 2, "Sequence must contain baseline and one forward migration")
        ordered_names = [item.get("file") for item in sorted(ordered_files, key=lambda item: item.get("order", 0))]
        require(
            ordered_names == ["postgresql.v0.2.0.sql", "postgresql.v0.2.1-review-versioning.sql"],
            f"Unexpected migration order: {ordered_names}",
        )

        baseline = DATABASE / ordered_names[0]
        migration = DATABASE / ordered_names[1]
        baseline_sql = read(baseline)
        migration_sql = read(migration)
        validate_transaction(baseline, baseline_sql)
        validate_transaction(migration, migration_sql)

        require("ADD COLUMN plan_group_id text" in migration_sql, "Assessment plan stable group id is required")
        require("assessment_plans_group_version_key" in migration_sql, "Assessment plan group/version uniqueness is required")
        require("assessment_plans_version_chain_check" in migration_sql, "Assessment plan version-chain check is required")
        require("CREATE TRIGGER assessment_plans_immutable" in migration_sql, "Assessment plans must become append-only")
        require("CREATE TRIGGER assessment_plan_version_chain" in migration_sql, "Assessment plan insertion chain must be validated")

        require("ADD COLUMN review_group_id text" in migration_sql, "Team review stable group id is required")
        require("team_reviews_group_version_key" in migration_sql, "Team review group/version uniqueness is required")
        require("team_reviews_supersedes_tenant_case_fkey" in migration_sql, "Team review supersedes FK must include institution and case")
        require("team_reviews_approved_members_check" in migration_sql, "Approved team review must include at least two members")
        require("CREATE TRIGGER team_review_version_chain" in migration_sql, "Team review insertion chain must be validated")
        require("report_requires_approved_team_review" in migration_sql, "Report creation must require an approved team review")
        require("CREATE VIEW current_assessment_plans\nWITH (security_invoker = true)" in migration_sql, "Current assessment-plan view must respect RLS")
        require("CREATE VIEW current_team_reviews\nWITH (security_invoker = true)" in migration_sql, "Current team-review view must respect RLS")

        for trigger_name in (
            "assessment_plan_version_chain",
            "team_review_version_chain",
            "report_requires_approved_team_review",
        ):
            require(trigger_name in migration_sql, f"Migration is missing trigger {trigger_name}")

        prohibited_patterns = (
            r"UPDATE\s+team_reviews\s+SET\s+status\s*=\s*'approved'",
            r"UPDATE\s+assessment_plans\s+SET\s+status\s*=\s*'approved'",
        )
        for pattern in prohibited_patterns:
            require(not re.search(pattern, migration_sql, flags=re.IGNORECASE), "Migration must not approve existing draft records by mutation")

        ordered_tests = sequence.get("ordered_tests")
        require(isinstance(ordered_tests, list) and len(ordered_tests) == 2, "Sequence must declare both smoke tests")
        test_names = [item.get("file") for item in sorted(ordered_tests, key=lambda item: item.get("order", 0))]
        require(
            test_names == ["tests/rls-smoke-v2.sql", "tests/review-versioning-smoke.sql"],
            f"Unexpected test order: {test_names}",
        )

        review_test = read(DATABASE / "tests" / "review-versioning-smoke.sql")
        required_negative_assertions = (
            "Assessment plan version skip was not blocked",
            "Append-only assessment plan update was not blocked",
            "Report creation from an unapproved team review was not blocked",
            "Append-only team review update was not blocked",
        )
        for assertion in required_negative_assertions:
            require(assertion in review_test, f"Review-versioning smoke test lacks negative assertion: {assertion}")
        require("current_plan_version <> 2" in review_test, "Smoke test must verify current plan view")
        require("current_review_version <> 2" in review_test, "Smoke test must verify current review view")
        require("NOBYPASSRLS" in review_test, "Smoke-test role must not bypass RLS")
        require("DROP OWNED BY pa_version_test" in review_test, "Smoke test must clean role grants")

        required_verification = set(sequence.get("required_verification", []))
        require(
            {
                "postgresql_15_execution",
                "postgresql_16_execution",
                "negative_version_chain_tests",
                "approved_team_review_report_gate",
            }.issubset(required_verification),
            "Migration sequence omits required execution evidence",
        )
    except SequenceFailure as exc:
        print(f"DATABASE SEQUENCE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated PostgreSQL 0.2.1 baseline-plus-migration sequence and review-versioning safety tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
