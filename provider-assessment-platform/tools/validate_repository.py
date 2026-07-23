#!/usr/bin/env python3
"""Validate the isolated provider-assessment platform using the standard library.

This validator checks structural safety properties that must hold before a
pathway can enter scientific review. It does not validate clinical accuracy or
replace publisher-specific scoring verification.
"""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.rules import PathwayConfigurationError, PathwayEngine  # noqa: E402


class ValidationFailure(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"Invalid JSON in {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def iter_transitions(pathway: Mapping[str, Any]) -> Iterable[tuple[str, Mapping[str, Any]]]:
    for node in pathway.get("nodes", []):
        for transition in node.get("transitions", []):
            yield node["id"], transition


def referenced_paths(expression: Any) -> set[str]:
    paths: set[str] = set()
    if not isinstance(expression, Mapping) or len(expression) != 1:
        return paths
    operator, operand = next(iter(expression.items()))
    if operator in {"all", "any"} and isinstance(operand, list):
        for child in operand:
            paths.update(referenced_paths(child))
    elif operator == "not":
        paths.update(referenced_paths(operand))
    elif operator == "exists" and isinstance(operand, str):
        paths.add(operand)
    elif operator in {"eq", "ne", "in", "contains", "gte", "gt", "lte", "lt", "count_gte"}:
        if isinstance(operand, list) and operand and isinstance(operand[0], str):
            paths.add(operand[0])
    return paths


def validate_catalog(path: Path) -> None:
    catalog = load_json(path)
    require(catalog.get("rules", {}).get("default_enabled") is False, "Catalog must default to disabled")
    require(catalog.get("rules", {}).get("unknown_license_blocks_use") is True, "Unknown licensing must block use")
    require(catalog.get("rules", {}).get("digital_use_requires_explicit_right") is True, "Digital use must require explicit rights")
    require(catalog.get("rules", {}).get("no_items_or_norm_tables_in_repository") is True, "Repository must prohibit protected items and norm tables")

    seen: set[str] = set()
    entries = catalog.get("entries")
    require(isinstance(entries, list) and entries, "Assessment catalog must contain entries")

    for entry in entries:
        entry_id = entry.get("id")
        require(isinstance(entry_id, str) and entry_id, "Catalog entry requires an id")
        require(entry_id not in seen, f"Duplicate catalog entry id: {entry_id}")
        seen.add(entry_id)

        enabled = entry.get("enabled") is True
        digital_status = entry.get("digital_right_status")
        blockers = entry.get("enablement_blockers", [])
        require(isinstance(blockers, list), f"{entry_id}: enablement_blockers must be a list")

        if enabled:
            require(
                digital_status in {"allowed", "allowed_after_governance_approval"},
                f"{entry_id}: enabled entry lacks an allowed digital-right status",
            )
            require(not blockers, f"{entry_id}: enabled entry still has unresolved blockers")
            require(
                entry.get("license_status") not in {"unknown", "commercial_restricted", "tool_specific_permission_required"},
                f"{entry_id}: enabled entry has unresolved licensing",
            )


def validate_reachability(pathway: Mapping[str, Any]) -> None:
    nodes = {node["id"]: node for node in pathway["nodes"]}
    start = pathway["entry"]["start_node"]
    queue: deque[str] = deque([start])
    reached: set[str] = set()

    while queue:
        node_id = queue.popleft()
        if node_id in reached:
            continue
        reached.add(node_id)
        for transition in nodes[node_id].get("transitions", []):
            destination = transition["destination"]
            if destination in nodes and destination not in reached:
                queue.append(destination)

    unreachable = sorted(set(nodes) - reached)
    require(not unreachable, f"{pathway['id']}: unreachable nodes: {unreachable}")


def validate_pathway(path: Path) -> None:
    pathway = load_json(path)
    try:
        PathwayEngine(pathway)
    except PathwayConfigurationError as exc:
        raise ValidationFailure(f"{path}: {exc}") from exc

    rules = pathway.get("global_rules", {})
    require(rules.get("prohibit_single_tool_conclusion") is True, f"{path}: single-tool conclusions must be prohibited")
    require(rules.get("minimum_independent_sources", 0) >= 2, f"{path}: at least two independent sources are required")
    require(rules.get("require_functional_profile") is True, f"{path}: functional profile must be required")
    require(rules.get("require_multidisciplinary_review") is True, f"{path}: multidisciplinary review must be required")

    governance = pathway.get("governance", {})
    source_ids = {item.get("id") for item in governance.get("source_register", [])}
    require(None not in source_ids and source_ids, f"{path}: source register is missing or malformed")

    for node_id, transition in iter_transitions(pathway):
        referenced = set(transition.get("source_ids", []))
        missing_sources = sorted(referenced - source_ids)
        require(not missing_sources, f"{path}: {node_id}/{transition['id']} references unknown sources {missing_sources}")
        require(
            isinstance(transition.get("condition"), Mapping),
            f"{path}: {node_id}/{transition['id']} condition must use the governed JSON rule language",
        )
        require(
            transition.get("requires_human_confirmation") is not None,
            f"{path}: {node_id}/{transition['id']} must state its confirmation requirement",
        )
        require(
            transition.get("blocks_automation") is not None,
            f"{path}: {node_id}/{transition['id']} must state whether automation is blocked",
        )

    high_impact_nodes = {"multidisciplinary-review", "professional-report", "closed"}
    node_ids = {node["id"] for node in pathway["nodes"]}
    require(high_impact_nodes.issubset(node_ids), f"{path}: required high-impact review nodes are missing")

    evidence_node = next((node for node in pathway["nodes"] if node["id"] == "evidence-collection"), None)
    require(evidence_node is not None, f"{path}: evidence-collection node is required")
    evidence_paths: set[str] = set()
    for transition in evidence_node.get("transitions", []):
        evidence_paths.update(referenced_paths(transition.get("condition")))
    require("sources" in evidence_paths, f"{path}: evidence routing must consider independent sources")
    require("completed_assessments" in evidence_paths, f"{path}: evidence routing must consider multiple assessments")
    require("quality.material_conflict_unresolved" in evidence_paths, f"{path}: evidence routing must consider unresolved conflicts")

    if pathway.get("status") == "approved":
        pending_values = json.dumps(pathway, ensure_ascii=False)
        require("PENDING:" not in pending_values, f"{path}: approved pathway contains pending governance fields")
        require("example.invalid" not in pending_values, f"{path}: approved pathway contains placeholder URLs")

    validate_reachability(pathway)


def validate_schemas() -> None:
    schema_files = sorted((ROOT / "schemas").glob("*.json"))
    require(schema_files, "No JSON schemas found")
    for path in schema_files:
        schema = load_json(path)
        require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", f"{path}: unsupported JSON Schema draft")
        require(isinstance(schema.get("$id"), str), f"{path}: schema id is required")


def main() -> int:
    try:
        validate_schemas()

        catalogs = sorted((ROOT / "registry").glob("assessment-catalog*.json"))
        require(len(catalogs) == 1, f"Expected exactly one active draft catalog, found {len(catalogs)}")
        validate_catalog(catalogs[0])

        pathways = sorted((ROOT / "pathways").glob("*.json"))
        require(pathways, "No pathway definitions found")
        for path in pathways:
            validate_pathway(path)

    except ValidationFailure as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print(f"Validated {len(pathways)} pathway(s), {len(catalogs)} catalog, and repository schemas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
