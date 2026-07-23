#!/usr/bin/env python3
"""Validate the active database baseline declared by MIGRATION_MANIFEST.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"
MANIFEST_PATH = DATABASE / "MIGRATION_MANIFEST.json"


class ActiveDatabaseFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ActiveDatabaseFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"Missing file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ActiveDatabaseFailure(f"Invalid JSON in {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def read(path: Path) -> str:
    require(path.is_file(), f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def table_block(sql: str, table_name: str) -> str:
    match = re.search(
        rf"CREATE\s+TABLE\s+{re.escape(table_name)}\s*\((.*?)\n\);",
        sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    require(match is not None, f"Missing CREATE TABLE {table_name}")
    return match.group(1)


def main() -> int:
    try:
        manifest = load_json(MANIFEST_PATH)
        active = manifest.get("active_baseline")
        require(isinstance(active, dict), "Manifest must define active_baseline")
        require(active.get("status") == "active-draft", "Active baseline must remain active-draft")
        require(active.get("approved_for_production") is False, "Draft database cannot be production-approved")
        require(manifest.get("minimum_postgresql_major") == 15, "PostgreSQL support floor must be 15")

        active_name = active.get("file")
        require(active_name == "postgresql.v0.2.0.sql", "Unexpected active baseline")
        sql_path = DATABASE / active_name
        sql = read(sql_path)
        upper = sql.upper()
        require(sql.lstrip().startswith("BEGIN;"), "Active baseline must begin with BEGIN")
        require(sql.rstrip().endswith("COMMIT;"), "Active baseline must end with COMMIT")

        for token in (
            "DISABLE ROW LEVEL SECURITY",
            "BYPASSRLS",
            "DROP TABLE",
            "DROP SCHEMA",
            "TRUNCATE ",
        ):
            require(token not in upper, f"Prohibited SQL in active baseline: {token.strip()}")

        required_tables = {
            "institutions",
            "providers",
            "provider_training_records",
            "assessment_catalog",
            "institution_assessment_authorizations",
            "provider_assessment_authorizations",
            "cases",
            "case_assignments",
            "consent_versions",
            "referrals",
            "information_sources",
            "safety_events",
            "safety_event_reviews",
            "pathway_instances",
            "pathway_events",
            "assessment_plans",
            "assessment_sessions",
            "assessment_session_deviations",
            "team_reviews",
            "report_versions",
            "audit_events",
        }
        created_tables = {
            name.lower()
            for name in re.findall(r"CREATE\s+TABLE\s+([a-z_][a-z0-9_]*)", sql, flags=re.IGNORECASE)
        }
        missing_tables = sorted(required_tables - created_tables)
        require(not missing_tables, f"Active baseline is missing tables: {missing_tables}")

        require("identity_vault_reference" in table_block(sql, "cases"), "Cases must reference an external identity vault")
        session_block = table_block(sql, "assessment_sessions").lower()
        require("result_reference" in session_block, "Sessions must use an opaque result reference")
        for prohibited_column in (
            "test_item",
            "test_items",
            "answer_key",
            "norm_table",
            "raw_item_response",
            "publisher_prompt",
        ):
            require(
                not re.search(rf"^\s*{prohibited_column}\s", session_block, flags=re.MULTILINE),
                f"Protected assessment column is prohibited: {prohibited_column}",
            )

        require("CREATE VIEW current_consents\nWITH (security_invoker = true)" in sql, "Consent view must be security-invoker")
        require("CREATE VIEW current_reports\nWITH (security_invoker = true)" in sql, "Report view must be security-invoker")
        require("ALTER TABLE %I ENABLE ROW LEVEL SECURITY" in sql, "RLS enablement loop is required")
        require("ALTER TABLE %I FORCE ROW LEVEL SECURITY" in sql, "Forced RLS is required")
        require("CREATE POLICY %I ON %I" in sql, "Dynamic policy construction must quote complete identifiers")
        require("CREATE POLICY assigned_case_access\nON cases\nAS RESTRICTIVE" in sql, "Case assignment policy clause order is invalid or missing")
        require("CREATE POLICY assignment_scope_access\nON case_assignments\nAS RESTRICTIVE" in sql, "Assignment policy must be restrictive")
        require("CREATE POLICY audit_event_insert_scope\nON audit_events\nAS RESTRICTIVE" in sql, "Audit insert policy must be restrictive")
        require(" AS RESTRICTIVE ON " not in upper, "Invalid CREATE POLICY clause order detected")

        composite_fk_count = len(
            re.findall(
                r"FOREIGN\s+KEY\s*\([^)]*institution_id[^)]*case_id[^)]*\)",
                sql,
                flags=re.IGNORECASE | re.DOTALL,
            )
        )
        require(composite_fk_count >= 15, f"Expected composite tenant-case foreign keys, found {composite_fk_count}")

        for table in (
            "consent_versions",
            "referrals",
            "information_sources",
            "safety_events",
            "safety_event_reviews",
            "pathway_events",
            "assessment_session_deviations",
            "team_reviews",
            "report_versions",
            "audit_events",
        ):
            require(
                re.search(
                    rf"BEFORE\s+UPDATE\s+OR\s+DELETE\s+ON\s+{re.escape(table)}",
                    sql,
                    flags=re.IGNORECASE,
                ) is not None,
                f"Immutable mutation trigger missing for {table}",
            )

        require("safety_event_blocks_case" in sql, "Urgent safety events must block routine case workflow")
        require("event_hash text NOT NULL UNIQUE" in sql, "Audit event hash must be required and unique")
        require("previous_event_hash" in sql, "Audit predecessor hash must be stored")

        retired = manifest.get("retired_drafts")
        require(isinstance(retired, list) and len(retired) == 3, "All 0.1.x drafts must be retired explicitly")
        retired_names = {item.get("file") for item in retired if isinstance(item, dict)}
        require(
            {
                "postgresql.v0.1.0.sql",
                "postgresql.v0.1.1-security-hardening.sql",
                "postgresql.v0.1.2-cross-tenant-integrity.sql",
            }.issubset(retired_names),
            "Retired migration list is incomplete",
        )

        smoke = read(DATABASE / "tests" / "rls-smoke-v2.sql")
        require("NOBYPASSRLS" in smoke, "Smoke-test role must not bypass RLS")
        require("Unassigned provider expected zero visible cases" in smoke, "Unassigned-provider negative test is required")
        require("Cross-tenant safety-event reference was not blocked" in smoke, "Cross-tenant negative test is required")
        require("Immutable safety event update was not blocked" in smoke, "Immutability negative test is required")
        require("DROP OWNED BY pa_app" in smoke, "Smoke test must clean grants before dropping its role")
    except ActiveDatabaseFailure as exc:
        print(f"ACTIVE DATABASE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated active PostgreSQL 0.2.0 baseline, retired migration manifest, and RLS smoke test v2.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
