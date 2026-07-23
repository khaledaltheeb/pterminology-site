#!/usr/bin/env python3
"""Static governance checks for PostgreSQL assessment-platform migrations.

These checks intentionally fail closed when critical RLS, immutability, tenant
integrity, or data-boundary markers disappear. They do not replace executing the
migrations against supported PostgreSQL versions and testing behavior there.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "database"


class DatabaseValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DatabaseValidationFailure(message)


def read(path: Path) -> str:
    require(path.is_file(), f"Missing migration: {path}")
    return path.read_text(encoding="utf-8")


def normalized_sql(sql: str) -> str:
    return re.sub(r"--.*?$", "", sql, flags=re.MULTILINE).strip()


def table_block(sql: str, table_name: str) -> str:
    pattern = re.compile(
        rf"CREATE\s+TABLE\s+{re.escape(table_name)}\s*\((.*?)\n\);",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(sql)
    require(match is not None, f"Missing CREATE TABLE {table_name}")
    return match.group(1)


def validate_transaction(path: Path, sql: str) -> None:
    cleaned = normalized_sql(sql)
    require(cleaned.upper().startswith("BEGIN;"), f"{path.name} must begin with BEGIN")
    require(cleaned.upper().endswith("COMMIT;"), f"{path.name} must end with COMMIT")
    prohibited = [
        "DISABLE ROW LEVEL SECURITY",
        "TRUNCATE ",
        "DROP SCHEMA",
        "DROP TABLE",
        "BYPASSRLS",
    ]
    upper = cleaned.upper()
    for token in prohibited:
        require(token not in upper, f"{path.name} contains prohibited SQL: {token.strip()}")


def validate_base(sql: str) -> None:
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
    created = set(re.findall(r"CREATE\s+TABLE\s+([a-z_][a-z0-9_]*)", sql, flags=re.IGNORECASE))
    missing = sorted(required_tables - {name.lower() for name in created})
    require(not missing, f"Base migration is missing required tables: {missing}")

    case_sql = table_block(sql, "cases").lower()
    require("identity_vault_reference" in case_sql, "cases must use an external identity-vault reference")
    prohibited_case_columns = {
        "full_name",
        "first_name",
        "last_name",
        "national_id",
        "passport_number",
        "street_address",
        "phone_number",
        "email_address",
        "guardian_name",
    }
    for column in prohibited_case_columns:
        require(not re.search(rf"^\s*{column}\s", case_sql, flags=re.MULTILINE), f"Direct identity column prohibited in cases: {column}")

    session_sql = table_block(sql, "assessment_sessions").lower()
    require("result_reference" in session_sql, "assessment_sessions must store only an opaque result reference")
    prohibited_session_columns = {
        "test_item",
        "test_items",
        "answer_key",
        "norm_table",
        "publisher_prompt",
        "raw_item_response",
    }
    for column in prohibited_session_columns:
        require(not re.search(rf"^\s*{column}\s", session_sql, flags=re.MULTILINE), f"Protected assessment column prohibited: {column}")

    immutable_tables = {
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
    }
    for table in immutable_tables:
        trigger_pattern = rf"BEFORE\s+UPDATE\s+OR\s+DELETE\s+ON\s+{re.escape(table)}"
        require(re.search(trigger_pattern, sql, flags=re.IGNORECASE), f"Immutable trigger missing for {table}")

    require("ALTER TABLE %I ENABLE ROW LEVEL SECURITY" in sql, "Base migration must enable RLS")
    require("ALTER TABLE %I FORCE ROW LEVEL SECURITY" in sql, "Base migration must force RLS")
    require("cases_version_on_update" in sql, "Case optimistic version trigger is required")
    require("safety_event_blocks_case" in sql, "Urgent safety events must place the case on hold")
    require("event_hash text NOT NULL UNIQUE" in sql, "Audit event hash must be mandatory and unique")
    require("previous_event_hash" in sql, "Audit hash-chain predecessor is required")


def validate_security_hardening(sql: str) -> None:
    require("CREATE POLICY assigned_case_access" in sql, "Assigned-case restrictive policy is required")
    require("AS RESTRICTIVE" in sql, "Case access policy must be restrictive")
    require("ALTER VIEW current_consents SET (security_invoker = true)" in sql, "Consent view must use security_invoker")
    require("ALTER VIEW current_reports SET (security_invoker = true)" in sql, "Report view must use security_invoker")
    require("current_setting('app.provider_id', true)" in sql, "Provider session context is required")
    require("current_setting('app.audit_scope', true)" in sql, "Explicit audit scope is required")

    case_scoped_tables = {
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
    }
    for table in case_scoped_tables:
        require(f"'{table}'" in sql, f"Assigned-case policy list is missing {table}")


def validate_cross_tenant_integrity(sql: str) -> None:
    required_composite_constraints = {
        "safety_events_tenant_case_key",
        "pathway_instances_tenant_case_key",
        "assessment_plans_tenant_case_key",
        "assessment_sessions_tenant_case_key",
        "team_reviews_tenant_case_key",
        "consent_versions_tenant_case_key",
        "report_versions_tenant_case_key",
        "safety_event_reviews_tenant_case_fkey",
        "pathway_events_tenant_case_fkey",
        "assessment_plans_pathway_tenant_case_fkey",
        "assessment_sessions_plan_tenant_case_fkey",
        "session_deviations_tenant_case_fkey",
        "team_reviews_pathway_tenant_case_fkey",
        "report_versions_review_tenant_case_fkey",
        "consent_versions_supersedes_tenant_case_fkey",
        "assessment_plans_supersedes_tenant_case_fkey",
        "report_versions_supersedes_tenant_case_fkey",
    }
    missing = sorted(name for name in required_composite_constraints if name not in sql)
    require(not missing, f"Cross-tenant migration is missing constraints: {missing}")

    triple_reference_pattern = re.compile(
        r"FOREIGN\s+KEY\s*\([^)]*institution_id[^)]*case_id[^)]*\)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    require(len(triple_reference_pattern.findall(sql)) >= 9, "Expected tenant-and-case composite foreign keys")
    require("DROP POLICY IF EXISTS audit_event_insert_scope" in sql, "Audit insert policy must be replaced")
    require("case_id IS NOT NULL" in sql and "case_id IS NULL" in sql, "Audit insert must distinguish case and institution events")


def main() -> int:
    migrations = [
        DATABASE / "postgresql.v0.1.0.sql",
        DATABASE / "postgresql.v0.1.1-security-hardening.sql",
        DATABASE / "postgresql.v0.1.2-cross-tenant-integrity.sql",
    ]

    try:
        sql_by_path = {path: read(path) for path in migrations}
        for path, sql in sql_by_path.items():
            validate_transaction(path, sql)
        validate_base(sql_by_path[migrations[0]])
        validate_security_hardening(sql_by_path[migrations[1]])
        validate_cross_tenant_integrity(sql_by_path[migrations[2]])

        readme = read(DATABASE / "README.md")
        require("PostgreSQL 15" in readme, "Database support floor must be documented")
        require("identity_vault_reference" in readme, "Identity boundary must be documented")
        require("BYPASSRLS" in readme, "BYPASSRLS prohibition must be documented")
        require("مواد اختبار" in readme, "Protected assessment-content boundary must be documented")
    except DatabaseValidationFailure as exc:
        print(f"DATABASE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {len(migrations)} ordered PostgreSQL migration(s) and database governance documentation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
