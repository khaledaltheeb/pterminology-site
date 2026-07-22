from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "data" / "content-entity-contract-v159.json"
ARABIC_RE = re.compile(r"[\u0600-\u06ff]")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ENTITY_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
SOURCE_ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")


@dataclass
class Finding:
    severity: str
    code: str
    file: str
    row: int | None
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "file": self.file,
            "row": self.row,
            "message": self.message,
        }


def split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def discover_files(root: Path) -> list[Path]:
    content = root / "content"
    if not content.is_dir():
        return []
    return sorted(path for path in content.glob("import-*.csv") if path.is_file())


def load_contract(root: Path) -> dict[str, object]:
    path = root / "data" / "content-entity-contract-v159.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_legacy_row(row: dict[str, str], file_name: str, row_number: int, contract: dict[str, object]) -> list[Finding]:
    findings: list[Finding] = []
    slug = row.get("slug", "").strip()
    ar = row.get("ar", "").strip()
    en = row.get("en", "").strip()
    description = row.get("description", "").strip()
    status = row.get("status", "").strip()
    reviewed_at = row.get("reviewed_at", "").strip()

    if not SLUG_RE.fullmatch(slug):
        findings.append(Finding("error", "invalid-slug", file_name, row_number, "slug must use lowercase kebab-case."))
    if not ar or not ARABIC_RE.search(ar):
        findings.append(Finding("error", "missing-arabic-title", file_name, row_number, "ar must contain an Arabic title."))
    if not en:
        findings.append(Finding("error", "missing-english-title", file_name, row_number, "en is required."))
    minimum = int(contract["rules"]["description_minimum_characters"])
    if len(description) < minimum:
        findings.append(Finding("error", "short-description", file_name, row_number, f"description must contain at least {minimum} characters."))
    if status not in {"draft", "reviewed", "published"}:
        findings.append(Finding("error", "invalid-legacy-status", file_name, row_number, f"Unsupported legacy status: {status!r}."))
    if status in {"reviewed", "published"} and not valid_date(reviewed_at):
        findings.append(Finding("error", "missing-review-date", file_name, row_number, "reviewed or published legacy rows require reviewed_at YYYY-MM-DD."))
    related = split_list(row.get("related", ""))
    if slug and slug in related:
        findings.append(Finding("error", "self-related", file_name, row_number, "A row cannot relate to its own slug."))
    if len(related) != len(set(related)):
        findings.append(Finding("error", "duplicate-related", file_name, row_number, "related contains duplicate slugs."))
    findings.append(Finding("warning", "legacy-v1-row", file_name, row_number, "Legacy v1 row is accepted during migration but lacks entity, audience, risk, review-status, and source identifiers."))
    return findings


def validate_v2_row(row: dict[str, str], file_name: str, row_number: int, contract: dict[str, object]) -> list[Finding]:
    findings: list[Finding] = []
    allowed = contract
    schema_version = row.get("schema_version", "").strip()
    entity_id = row.get("entity_id", "").strip()
    slug = row.get("slug", "").strip()
    content_type = row.get("content_type", "").strip()
    ar = row.get("ar", "").strip()
    en = row.get("en", "").strip()
    audience = row.get("audience", "").strip()
    age_group = row.get("age_group", "").strip()
    risk_level = row.get("risk_level", "").strip()
    description = row.get("description", "").strip()
    status = row.get("status", "").strip()
    review_status = row.get("review_status", "").strip()
    reviewed_at = row.get("reviewed_at", "").strip()
    source_ids = split_list(row.get("source_ids", ""))
    keywords = split_list(row.get("keywords", ""))
    related = split_list(row.get("related", ""))

    if schema_version != contract["schema_version"]:
        findings.append(Finding("error", "invalid-schema-version", file_name, row_number, f"schema_version must be {contract['schema_version']}."))
    if not ENTITY_ID_RE.fullmatch(entity_id):
        findings.append(Finding("error", "invalid-entity-id", file_name, row_number, "entity_id must use lowercase dot or kebab notation."))
    if not SLUG_RE.fullmatch(slug):
        findings.append(Finding("error", "invalid-slug", file_name, row_number, "slug must use lowercase kebab-case."))
    if content_type not in set(contract["allowed_content_types"]):
        findings.append(Finding("error", "invalid-content-type", file_name, row_number, f"Unsupported content_type: {content_type!r}."))
    if not ar or not ARABIC_RE.search(ar):
        findings.append(Finding("error", "missing-arabic-title", file_name, row_number, "ar must contain an Arabic title."))
    if not en:
        findings.append(Finding("error", "missing-english-title", file_name, row_number, "en is required."))
    if audience not in set(contract["allowed_audiences"]):
        findings.append(Finding("error", "invalid-audience", file_name, row_number, f"Unsupported audience: {audience!r}."))
    if age_group not in set(contract["allowed_age_groups"]):
        findings.append(Finding("error", "invalid-age-group", file_name, row_number, f"Unsupported age_group: {age_group!r}."))
    if risk_level not in set(contract["allowed_risk_levels"]):
        findings.append(Finding("error", "invalid-risk-level", file_name, row_number, f"Unsupported risk_level: {risk_level!r}."))
    minimum = int(contract["rules"]["description_minimum_characters"])
    if len(description) < minimum:
        findings.append(Finding("error", "short-description", file_name, row_number, f"description must contain at least {minimum} characters."))
    minimum_keywords = int(contract["rules"]["minimum_keywords"])
    if len(keywords) < minimum_keywords:
        findings.append(Finding("error", "insufficient-keywords", file_name, row_number, f"At least {minimum_keywords} distinct keywords are required."))
    if len(keywords) != len(set(keywords)):
        findings.append(Finding("error", "duplicate-keywords", file_name, row_number, "keywords contains duplicate values."))
    if slug and slug in related:
        findings.append(Finding("error", "self-related", file_name, row_number, "A row cannot relate to its own slug."))
    if len(related) != len(set(related)):
        findings.append(Finding("error", "duplicate-related", file_name, row_number, "related contains duplicate slugs."))
    if len(source_ids) != len(set(source_ids)) or any(not SOURCE_ID_RE.fullmatch(item) for item in source_ids):
        findings.append(Finding("error", "invalid-source-ids", file_name, row_number, "source_ids must be unique stable identifiers separated by |."))
    if status not in set(contract["allowed_statuses"]):
        findings.append(Finding("error", "invalid-status", file_name, row_number, f"Unsupported status: {status!r}."))
    if review_status not in set(contract["allowed_review_statuses"]):
        findings.append(Finding("error", "invalid-review-status", file_name, row_number, f"Unsupported review_status: {review_status!r}."))

    if status == "published":
        if not valid_date(reviewed_at):
            findings.append(Finding("error", "missing-review-date", file_name, row_number, "Published rows require reviewed_at YYYY-MM-DD."))
        if risk_level == "moderate" and len(source_ids) < int(contract["rules"]["published_moderate_minimum_source_ids"]):
            findings.append(Finding("error", "insufficient-sources", file_name, row_number, "Published moderate-risk content requires at least one source_id."))
        if risk_level == "high":
            if len(source_ids) < int(contract["rules"]["published_high_minimum_source_ids"]):
                findings.append(Finding("error", "insufficient-sources", file_name, row_number, "Published high-risk content requires at least two source_ids."))
            if review_status in {"unreviewed", "needs-specialist-review"}:
                findings.append(Finding("error", "insufficient-review", file_name, row_number, "Published high-risk content must have completed review status."))
        if risk_level == "critical" and review_status != "externally-reviewed":
            findings.append(Finding("error", "critical-review-required", file_name, row_number, "Published critical-risk content requires externally-reviewed status."))
    elif reviewed_at and not valid_date(reviewed_at):
        findings.append(Finding("error", "invalid-review-date", file_name, row_number, "reviewed_at must use YYYY-MM-DD when present."))

    return findings


def audit(root: Path) -> dict[str, object]:
    contract = load_contract(root)
    legacy_header = list(contract["legacy_v1_columns"])
    v2_required = set(contract["v2_required_columns"])
    findings: list[Finding] = []
    records: list[dict[str, object]] = []
    seen_entity_ids: dict[str, tuple[str, int]] = {}
    seen_slugs: dict[str, tuple[str, int]] = {}

    for path in discover_files(root):
        relative = path.relative_to(root).as_posix()
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames or []
            is_legacy = header == legacy_header
            is_v2 = v2_required <= set(header)
            if not is_legacy and not is_v2:
                findings.append(Finding("error", "invalid-header", relative, None, "CSV header matches neither legacy v1 nor required v2 columns."))
                continue
            for row_number, row in enumerate(reader, start=2):
                if not any((value or "").strip() for value in row.values()):
                    continue
                row_findings = validate_legacy_row(row, relative, row_number, contract) if is_legacy else validate_v2_row(row, relative, row_number, contract)
                findings.extend(row_findings)
                slug = row.get("slug", "").strip()
                entity_id = row.get("entity_id", "").strip() if is_v2 else ""
                if slug:
                    if slug in seen_slugs:
                        first_file, first_row = seen_slugs[slug]
                        findings.append(Finding("error", "duplicate-slug", relative, row_number, f"slug already appears at {first_file}:{first_row}."))
                    else:
                        seen_slugs[slug] = (relative, row_number)
                if entity_id:
                    if entity_id in seen_entity_ids:
                        first_file, first_row = seen_entity_ids[entity_id]
                        findings.append(Finding("error", "duplicate-entity-id", relative, row_number, f"entity_id already appears at {first_file}:{first_row}."))
                    else:
                        seen_entity_ids[entity_id] = (relative, row_number)
                records.append({
                    "file": relative,
                    "row": row_number,
                    "format": "legacy-v1" if is_legacy else "v2",
                    "entity_id": entity_id or None,
                    "slug": slug or None,
                    "content_type": row.get("content_type") or None,
                    "risk_level": row.get("risk_level") or None,
                    "status": row.get("status") or None,
                    "error_count": sum(item.severity == "error" for item in row_findings),
                    "warning_count": sum(item.severity == "warning" for item in row_findings),
                })

    errors = [item.as_dict() for item in findings if item.severity == "error"]
    warnings = [item.as_dict() for item in findings if item.severity == "warning"]
    return {
        "version": "159-content-entity-import",
        "schema_version": contract["schema_version"],
        "files_scanned": len(discover_files(root)),
        "records_scanned": len(records),
        "legacy_records": sum(item["format"] == "legacy-v1" for item in records),
        "v2_records": sum(item["format"] == "v2" for item in records),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors[:1000],
        "warnings": warnings[:2000],
        "records": records,
        "policy": {
            "legacy_v1_is_warning_not_error": True,
            "new_batches_require_v2": True,
            "automatic_publication": False,
            "automatic_deletion_or_noindex": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate psychology content import CSV files.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--output", default="artifacts/content-import-v159.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = audit(root)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("files_scanned", "records_scanned", "legacy_records", "v2_records", "error_count", "warning_count")}, ensure_ascii=False, indent=2))
    if report["error_count"]:
        raise SystemExit("\n".join(f"{item['file']}:{item['row']}: {item['message']}" for item in report["errors"][:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
