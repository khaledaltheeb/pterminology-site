#!/usr/bin/env python3
"""Validate cross-file safety invariants for governed assessment pathways."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class CrossReferenceFailure(RuntimeError):
    pass


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CrossReferenceFailure(f"Invalid JSON in {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CrossReferenceFailure(message)


def main() -> int:
    try:
        catalog_files = sorted((ROOT / "registry").glob("assessment-catalog*.json"))
        require(len(catalog_files) == 1, "Exactly one assessment catalog is required")
        catalog = load(catalog_files[0])
        catalog_entries = catalog.get("entries", [])
        catalog_ids = {entry.get("id") for entry in catalog_entries}
        require(None not in catalog_ids and catalog_ids, "Catalog entries require unique ids")
        require(len(catalog_ids) == len(catalog_entries), "Duplicate catalog ids detected")

        pathway_files = sorted((ROOT / "pathways").glob("*.json"))
        require(pathway_files, "At least one pathway is required")

        for path in pathway_files:
            pathway = load(path)
            pathway_id = pathway.get("id", path.name)
            nodes = pathway.get("nodes", [])
            node_ids = {node.get("id") for node in nodes}

            used_assessment_ids: set[str] = set()
            for node in nodes:
                node_id = node.get("id")
                used_assessment_ids.update(node.get("assessment_ids", []))

                for transition in node.get("transitions", []):
                    destination = transition.get("destination")
                    if destination in {"multidisciplinary-review", "professional-report", "closed"}:
                        require(
                            transition.get("requires_human_confirmation") is True,
                            f"{pathway_id}: {node_id}/{transition.get('id')} reaches {destination} without human confirmation",
                        )
                        require(
                            transition.get("blocks_automation") is True,
                            f"{pathway_id}: {node_id}/{transition.get('id')} reaches {destination} without blocking automation",
                        )

                    if node_id == "evidence-collection":
                        require(
                            destination not in {"professional-report", "closed"},
                            f"{pathway_id}: evidence collection cannot bypass professional review",
                        )

            unknown_tools = sorted(used_assessment_ids - catalog_ids)
            require(
                not unknown_tools,
                f"{pathway_id}: pathway references tools absent from catalog: {unknown_tools}",
            )

            require(
                {"evidence-collection", "multidisciplinary-review", "professional-report", "closed"}.issubset(node_ids),
                f"{pathway_id}: required review and closure nodes are missing",
            )

        for entry in catalog_entries:
            entry_id = entry["id"]
            digital_status = entry.get("digital_right_status")
            if digital_status in {"blocked", "blocked_until_specific_tool_approved"}:
                require(entry.get("enabled") is False, f"{entry_id}: blocked digital right cannot be enabled")
            if entry.get("license_status") in {
                "commercial_restricted",
                "commercial_or_permission_required",
                "commercial_restricted_and_training_required",
                "electronic_license_review_required",
                "tool_specific_permission_required",
            }:
                require(entry.get("enabled") is False, f"{entry_id}: unresolved license cannot be enabled")

    except CrossReferenceFailure as exc:
        print(f"CROSS-REFERENCE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print(
        f"Validated {len(pathway_files)} pathway(s) against {len(catalog_ids)} registered assessment entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
