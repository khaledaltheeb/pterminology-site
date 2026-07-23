#!/usr/bin/env python3
"""Validate the PostgreSQL 0.2.3 intake-alignment migration sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST = DATABASE / "MIGRATION_SEQUENCE.v0.2.3.json"


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


def validate_transaction(path: Path, sql: str) -> None:
    require(sql.lstrip().startswith("BEGIN;"), f"{path.name} must begin with BEGIN")
    require(sql.rstrip().endswith("COMMIT;"), f"{path.name} must end with COMMIT")
    upper = sql.upper()
    for token in ("BYPASSRLS", "DROP TABLE", "DROP SCHEMA", "TRUNCATE "):
        require(token not in upper, f"{path.name} contains prohibited SQL: {token.strip()}")


def main() -> int:
    try:
        manifest = load(MANIFEST)
        require(manifest.get("sequence_version") == "0.2.3", "Unexpected sequence version")
        require(manifest.get("status") == "active-draft", "Sequence must remain active-draft")
        require(manifest.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must remain 15")
        require(manifest.get("supersedes_sequence") == "0.2.2", "Sequence must explicitly supersede 0.2.2")

        ordered_files = sorted(
            manifest.get("ordered_files", []),
            key=lambda item: item.get("order", 0),
        )
        expected_files = [
            "postgresql.v0.2.0.sql",
            "postgresql.v0.2.2-review-versioning.sql",
            "postgresql.v0.2.3-intake-alignment.sql",
        ]
        file_names = [item.get("file") for item in ordered_files]
        require(file_names == expected_files, f"Unexpected active sequence: {file_names}")

        for file_name in expected_files:
            path = DATABASE / file_name
            validate_transaction(path, read(path))

        migration = read(DATABASE / expected_files[-1])
        required_controls = (
            "ADD COLUMN safety_screened_at timestamptz",
            "ADD COLUMN safety_screened_by_provider_id text",
            "ADD COLUMN intake_safety_actions jsonb",
            "legacy_record_requires_safety_action_review",
            "cases_intake_safety_actions_array_check",
            "cases_safety_screened_by_tenant_fkey",
            "jsonb_array_length(intake_safety_actions) >= 1",
            "REFERENCES providers(provider_id, institution_id)",
        )
        for control in required_controls:
            require(control in migration, f"Intake migration is missing control: {control}")

        require(
            "COALESCE" in migration and "FROM safety_events safety_event" in migration,
            "Legacy backfill must preserve the earliest documented safety actions when available",
        )
        require(
            "ALTER COLUMN safety_screened_at SET NOT NULL" in migration
            and "ALTER COLUMN intake_safety_actions SET NOT NULL" in migration,
            "Aligned intake fields must become mandatory after backfill",
        )

        fixtures = manifest.get("pre_migration_fixtures")
        require(isinstance(fixtures, list) and len(fixtures) == 1, "One legacy fixture is required")
        require(fixtures[0].get("before_order") == 3, "Legacy fixture must run immediately before 0.2.3")
        require(
            fixtures[0].get("file") == "tests/intake-alignment-legacy-seed.sql",
            "Unexpected legacy intake fixture",
        )

        seed = read(DATABASE / "tests" / "intake-alignment-legacy-seed.sql")
        check = read(DATABASE / "tests" / "intake-alignment-backfill-check.sql")
        require("CASE-ALIGN0001" in seed, "Legacy intake seed must create a pre-alignment case")
        require(
            "safety_screened_at" not in seed.split("INSERT INTO cases", 1)[1].split(");", 1)[0],
            "Legacy fixture must use the pre-0.2.3 case column set",
        )
        require(
            "legacy_record_requires_safety_action_review" in check,
            "Backfill check must require the conservative legacy marker",
        )
        require(
            "Empty intake safety actions were not rejected" in check,
            "Backfill test must reject an empty safety-action array",
        )

        required_verification = set(manifest.get("required_verification", []))
        for requirement in (
            "postgresql_15_execution",
            "postgresql_16_execution",
            "existing_case_intake_backfill_test",
            "negative_empty_safety_action_test",
            "backup_restore_test",
        ):
            require(requirement in required_verification, f"Missing required verification: {requirement}")
    except ValidationFailure as exc:
        print(f"DATABASE 0.2.3 VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated PostgreSQL 0.2.3 intake alignment, conservative legacy backfill, and mandatory safety-action controls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
