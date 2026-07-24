#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "external-review-register-v201.json"
SCAN_ROOTS = (ROOT / "content", ROOT / "data")
REVIEW_STATUS = "needs-external-review"
PENDING_DECISION = "awaiting-independent-review"
SOURCE_FIELDS = {"publisher", "title", "url", "verified_at", "review_focus"}
REVIEWER_FIELDS = {"role", "minimum_basis", "required"}
ITEM_FIELDS = {
    "id",
    "source_path",
    "current_review_status",
    "publication_block",
    "risk_domains",
    "required_reviewer_roles",
    "authoritative_review_sources",
    "acceptance_criteria",
    "open_evidence",
    "decision",
}
DATE_RE = re.compile(r"^20\d{2}-\d{2}-\d{2}$")


class ValidationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationError(f"Invalid JSON at {path.relative_to(ROOT)}: {exc}") from exc


def externally_blocked_sources(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for base_name in ("content", "data"):
        base = root / base_name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(payload, dict) and payload.get("review_status") == REVIEW_STATUS:
                found[path.relative_to(root).as_posix()] = payload
    return found


def validate_register(payload: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("version") != 201:
        errors.append("register version must equal 201")
    if payload.get("status") != "open":
        errors.append("register status must remain open while blocked items exist")
    if not DATE_RE.fullmatch(str(payload.get("updated_at", ""))):
        errors.append("updated_at must use YYYY-MM-DD")
    if not isinstance(payload.get("review_evidence_required"), list) or len(payload["review_evidence_required"]) < 10:
        errors.append("review_evidence_required must define a substantial evidence record")
    if not isinstance(payload.get("allowed_decisions"), list) or "approve-within-defined-scope" not in payload["allowed_decisions"]:
        errors.append("allowed_decisions must include bounded approval")
    if "separate audited commit" not in str(payload.get("publication_rule", "")):
        errors.append("publication_rule must require a separate audited status change")

    items = payload.get("items")
    if not isinstance(items, list):
        errors.append("items must be a list")
        items = []

    blocked = externally_blocked_sources(root)
    by_path: dict[str, dict[str, Any]] = {}
    ids: set[str] = set()
    for index, item in enumerate(items):
        prefix = f"items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing = ITEM_FIELDS - set(item)
        if missing:
            errors.append(f"{prefix} missing fields: {sorted(missing)}")
            continue
        item_id = str(item["id"])
        path = str(item["source_path"])
        if item_id in ids:
            errors.append(f"duplicate item id: {item_id}")
        ids.add(item_id)
        if path in by_path:
            errors.append(f"duplicate source_path: {path}")
        by_path[path] = item
        source_file = root / path
        if not source_file.is_file():
            errors.append(f"registered source does not exist: {path}")
            continue
        source_payload = blocked.get(path)
        if source_payload is None:
            errors.append(f"registered source is not currently {REVIEW_STATUS}: {path}")
        if item["current_review_status"] != REVIEW_STATUS:
            errors.append(f"{path} current_review_status must equal {REVIEW_STATUS}")
        if item["publication_block"] is not True:
            errors.append(f"{path} publication_block must be true")
        if item["decision"] != PENDING_DECISION:
            errors.append(f"{path} decision must remain {PENDING_DECISION}")
        if item["open_evidence"] != []:
            errors.append(f"{path} open_evidence must remain empty until real evidence is added")
        if not isinstance(item["risk_domains"], list) or len(item["risk_domains"]) < 4:
            errors.append(f"{path} must declare at least four risk domains")
        roles = item["required_reviewer_roles"]
        if not isinstance(roles, list) or len(roles) < 4:
            errors.append(f"{path} must require at least four reviewer roles")
        else:
            role_names: set[str] = set()
            for role in roles:
                if not isinstance(role, dict) or REVIEWER_FIELDS - set(role):
                    errors.append(f"{path} contains an incomplete reviewer role")
                    continue
                if role["required"] is not True:
                    errors.append(f"{path} reviewer role {role.get('role')} must remain required")
                role_name = str(role["role"])
                if role_name in role_names:
                    errors.append(f"{path} duplicate reviewer role: {role_name}")
                role_names.add(role_name)
                if len(str(role["minimum_basis"]).strip()) < 40:
                    errors.append(f"{path} reviewer role {role_name} has an insufficient minimum_basis")
        sources = item["authoritative_review_sources"]
        if not isinstance(sources, list) or len(sources) < 3:
            errors.append(f"{path} must cite at least three authoritative review sources")
        else:
            urls: set[str] = set()
            for source in sources:
                if not isinstance(source, dict) or SOURCE_FIELDS - set(source):
                    errors.append(f"{path} contains an incomplete authoritative source")
                    continue
                url = str(source["url"])
                if not url.startswith("https://"):
                    errors.append(f"{path} source must use HTTPS: {url}")
                if url in urls:
                    errors.append(f"{path} duplicate authoritative source: {url}")
                urls.add(url)
                if not DATE_RE.fullmatch(str(source["verified_at"])):
                    errors.append(f"{path} source verified_at must use YYYY-MM-DD")
                if not isinstance(source["review_focus"], list) or len(source["review_focus"]) < 3:
                    errors.append(f"{path} source must define at least three review_focus entries")
        criteria = item["acceptance_criteria"]
        if not isinstance(criteria, list) or len(criteria) < 8:
            errors.append(f"{path} must define at least eight acceptance criteria")
        elif any(len(str(criterion).strip()) < 45 for criterion in criteria):
            errors.append(f"{path} contains an acceptance criterion that is too vague")

        if source_payload:
            if source_payload.get("default_publishable") is True:
                errors.append(f"{path} cannot be default_publishable while externally blocked")
            if path.endswith("urgent-help-governance.json") and source_payload.get("services") != []:
                errors.append("urgent-help governance services must remain empty until jurisdictional verification")

    registered = set(by_path)
    blocked_paths = set(blocked)
    missing_from_register = sorted(blocked_paths - registered)
    stale_register_items = sorted(registered - blocked_paths)
    if missing_from_register:
        errors.append(f"externally blocked sources missing from register: {missing_from_register}")
    if stale_register_items:
        errors.append(f"register contains sources that are no longer externally blocked: {stale_register_items}")

    if errors:
        raise ValidationError("\n".join(errors))
    return {
        "version": 201,
        "status": "pass",
        "blocked_source_count": len(blocked_paths),
        "registered_item_count": len(registered),
        "all_publication_blocks_active": True,
        "all_decisions_pending": True,
        "registered_paths": sorted(registered),
    }


def main() -> int:
    try:
        payload = load_json(REGISTER)
        if not isinstance(payload, dict):
            raise ValidationError("register root must be an object")
        report = validate_register(payload)
    except ValidationError as exc:
        print(json.dumps({"version": 201, "status": "fail", "errors": str(exc).splitlines()}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
