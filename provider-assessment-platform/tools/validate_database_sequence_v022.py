#!/usr/bin/env python3
"""Validate the corrected PostgreSQL 0.2.2 migration sequence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST = DATABASE / "MIGRATION_SEQUENCE.v0.2.2.json"


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


def position(sql: str, token: str) -> int:
    index = sql.find(token)
    require(index >= 0, f"Migration is missing token: {token}")
    return index


def validate_transaction(path: Path, sql: str) -> None:
    require(sql.lstrip().startswith("BEGIN;"), f"{path.name} must begin with BEGIN")
    require(sql.rstrip().endswith("COMMIT;"), f"{path.name} must end with COMMIT")
    upper = sql.upper()
    for token in ("BYPASSRLS", "DROP TABLE", "DROP SCHEMA", "TRUNCATE "):
        require(token not in upper, f"{path.name} contains prohibited SQL: {token.strip()}")


def main() -> int:
    try:
        manifest = load(MANIFEST)
        require(manifest.get("sequence_version") == "0.2.2", "Unexpected active sequence version")
        require(manifest.get("status") == "active-draft", "Sequence must remain active-draft")
        require(manifest.get("approved_for_production") is False, "Draft sequence cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must remain 15")

        ordered_files = manifest.get("ordered_files")
        require(isinstance(ordered_files, list) and len(ordered_files) == 2, "Expected baseline and corrected migration")
        ordered_files = sorted(ordered_files, key=lambda item: item.get("order", 0))
        file_names = [item.get("file") for item in ordered_files]
        require(
            file_names == ["postgresql.v0.2.0.sql", "postgresql.v0.2.2-review-versioning.sql"],
            f"Unexpected active sequence: {file_names}",
        )

        baseline_path = DATABASE / file_names[0]
        migration_path = DATABASE / file_names[1]
        baseline = read(baseline_path)
        migration = read(migration_path)
        validate_transaction(baseline_path, baseline)
        validate_transaction(migration_path, migration)

        disable = position(migration, "ALTER TABLE team_reviews DISABLE TRIGGER team_reviews_immutable;")
        update = position(migration, "UPDATE team_reviews review")
        enable = position(migration, "ALTER TABLE team_reviews ENABLE TRIGGER team_reviews_immutable;")
        not_null = position(migration, "ALTER COLUMN review_group_id SET NOT NULL")
        require(disable < update < enable < not_null, "Immutable team-review trigger must be disabled only around legacy backfill and restored before constraints")
        require(migration.count("DISABLE TRIGGER") == 1, "Only the targeted immutable trigger may be disabled")
        require(migration.count("ENABLE TRIGGER") == 1, "The targeted immutable trigger must be restored exactly once")
        require("transactional DDL restores" in migration, "Migration must document rollback safety for temporary trigger disablement")

        required_controls = (
            "assessment_plans_group_version_key",
            "assessment_plans_version_chain_check",
            "assessment_plans_immutable",
            "assessment_plan_version_chain",
            "team_reviews_group_version_key",
            "team_reviews_supersedes_tenant_case_fkey",
            "team_reviews_approved_members_check",
            "team_review_version_chain",
            "report_requires_approved_team_review",
            "current_assessment_plans",
            "current_team_reviews",
            "security_invoker = true",
        )
        for control in required_controls:
            require(control in migration, f"Corrected migration is missing control: {control}")

        retired = manifest.get("retired_sequences")
        require(isinstance(retired, list) and retired, "Corrected manifest must retain the retired 0.2.1 sequence")
        retired_021 = next((item for item in retired if item.get("sequence") == "0.2.1"), None)
        require(isinstance(retired_021, dict), "0.2.1 must be explicitly retired")
        require(retired_021.get("migration") == "postgresql.v0.2.1-review-versioning.sql", "Retired migration reference is incorrect")
        require("immutable" in retired_021.get("reason", "").lower(), "Retirement reason must record the immutable-trigger defect")

        seed = read(DATABASE / "tests" / "review-versioning-legacy-seed.sql")
        backfill = read(DATABASE / "tests" / "review-versioning-backfill-check.sql")
        chain = read(DATABASE / "tests" / "review-versioning-smoke.sql")
        require("PLAN-BLEGACY01" in seed and "TREV-BLEGACY01" in seed, "Legacy seed must create both pre-versioning record types")
        require("created_by_provider_id" not in seed.split("INSERT INTO team_reviews", 1)[1].split(");", 1)[0], "Legacy team-review fixture must use the pre-migration column set")
        require("Team-review immutability trigger was not restored" in backfill, "Backfill check must verify trigger restoration")
        require("Legacy team review creator was not derived correctly" in backfill, "Backfill check must verify creator derivation")
        require("SYNTHETIC-LEGACY-BACKFILL-REPORT" in backfill, "Backfill check must verify approved legacy review can support a report")
        require("Report creation from an unapproved team review was not blocked" in chain, "Version-chain tests must retain the negative report gate")
        require("Assessment plan version skip was not blocked" in chain, "Version-chain tests must reject skipped versions")

        required_verification = set(manifest.get("required_verification", []))
        require("existing_team_review_backfill_test" in required_verification, "Manifest must require existing-row migration evidence")
        require("postgresql_15_execution" in required_verification, "Manifest must require PostgreSQL 15 execution")
        require("postgresql_16_execution" in required_verification, "Manifest must require PostgreSQL 16 execution")
        require("backup_restore_test" in required_verification, "Manifest must keep backup/restore evidence pending")
    except ValidationFailure as exc:
        print(f"DATABASE 0.2.2 VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated corrected PostgreSQL 0.2.2 sequence, retired 0.2.1 record, and legacy-backfill safety tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
