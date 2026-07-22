from __future__ import annotations

import argparse
import ast
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "topic-cluster-registry-v160.json"
GENERATOR_PATH = ROOT / "scripts" / "scale_site_v8.py"
ID_RE = re.compile(r"^[a-z0-9]+(?:[.-][a-z0-9]+)*$")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEGACY_CONCEPT_RE = re.compile(r"^/pterminology-site/encyclopedia/concept-(\d{4})/$")
LEGACY_HUB_RE = re.compile(r"^/pterminology-site/hubs/hub-(\d{3})/$")


@dataclass
class Finding:
    severity: str
    code: str
    cluster_id: str | None
    node_id: str | None
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "severity": self.severity,
            "code": self.code,
            "cluster_id": self.cluster_id,
            "node_id": self.node_id,
            "message": self.message,
        }


def extract_literal_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise ValueError(f"Could not find literal assignment {name} in {path}")


def expected_hubs(start: int, end: int) -> list[str]:
    first = math.ceil(start / 10)
    last = math.ceil(end / 10)
    return [f"/pterminology-site/hubs/hub-{number:03d}/" for number in range(first, last + 1)]


def validate_registry(registry: dict[str, Any], domains: list[Any], facets: list[Any]) -> dict[str, Any]:
    findings: list[Finding] = []
    policy = registry.get("policy", {})
    clusters = registry.get("clusters", [])
    cluster_ids: set[str] = set()
    cluster_slugs: set[str] = set()
    global_node_ids: set[str] = set()
    global_intents: set[str] = set()
    global_proposed_slugs: set[str] = set()

    required_policy_true = {
        "automatic_publication": False,
        "automatic_redirects": False,
        "automatic_canonical_changes": False,
        "automatic_delete_merge_or_noindex": False,
        "preserve_existing_urls_until_approved_migration": True,
        "one_pillar_per_cluster": True,
        "unique_search_intent_per_node": True,
    }
    for key, expected in required_policy_true.items():
        if policy.get(key) is not expected:
            findings.append(Finding("error", "unsafe-policy", None, None, f"policy.{key} must be {expected!r}."))

    for cluster in clusters:
        cluster_id = str(cluster.get("cluster_id", ""))
        cluster_slug = str(cluster.get("slug", ""))
        if not ID_RE.fullmatch(cluster_id):
            findings.append(Finding("error", "invalid-cluster-id", cluster_id or None, None, "cluster_id must use lowercase dot or kebab notation."))
        if not SLUG_RE.fullmatch(cluster_slug):
            findings.append(Finding("error", "invalid-cluster-slug", cluster_id or None, None, "cluster slug must use lowercase kebab-case."))
        if cluster_id in cluster_ids:
            findings.append(Finding("error", "duplicate-cluster-id", cluster_id, None, "cluster_id is duplicated."))
        cluster_ids.add(cluster_id)
        if cluster_slug in cluster_slugs:
            findings.append(Finding("error", "duplicate-cluster-slug", cluster_id, None, "cluster slug is duplicated."))
        cluster_slugs.add(cluster_slug)

        legacy = cluster.get("legacy_generation", {})
        position = legacy.get("domain_position")
        if not isinstance(position, int) or not (1 <= position <= len(domains)):
            findings.append(Finding("error", "invalid-domain-position", cluster_id, None, "legacy domain_position is outside generator DOMAINS."))
            continue
        domain_ar, domain_en, _category = domains[position - 1]
        if legacy.get("domain_ar") != domain_ar or legacy.get("domain_en") != domain_en:
            findings.append(Finding("error", "legacy-domain-mismatch", cluster_id, None, "Registry domain names do not match scale_site_v8.py DOMAINS."))
        if legacy.get("facet_count") != len(facets):
            findings.append(Finding("error", "facet-count-mismatch", cluster_id, None, "legacy facet_count does not match scale_site_v8.py FACETS."))

        expected_start = (position - 1) * len(facets) + 1
        expected_end = expected_start + len(facets) - 1
        start = legacy.get("concept_start")
        end = legacy.get("concept_end")
        if (start, end) != (expected_start, expected_end):
            findings.append(Finding("error", "legacy-range-mismatch", cluster_id, None, f"Expected legacy concept range {expected_start}-{expected_end}, found {start}-{end}."))
        if legacy.get("legacy_hubs") != expected_hubs(expected_start, expected_end):
            findings.append(Finding("error", "legacy-hub-mismatch", cluster_id, None, "legacy_hubs do not match groups-of-ten generated by scale_site_v8.py."))
        if legacy.get("canonical_policy") != "preserve-until-semantic-replacement-is-reviewed-and-approved":
            findings.append(Finding("error", "unsafe-canonical-policy", cluster_id, None, "Existing canonicals must be preserved until an approved migration."))

        pillar = cluster.get("pillar")
        if not isinstance(pillar, dict):
            findings.append(Finding("error", "missing-pillar", cluster_id, None, "Each cluster requires exactly one pillar object."))
            node_records: list[dict[str, Any]] = list(cluster.get("nodes", []))
        else:
            node_records = [pillar, *list(cluster.get("nodes", []))]

        assigned_numbers: set[int] = set()
        local_node_ids: set[str] = set()
        local_intents: set[str] = set()
        local_slugs: set[str] = set()
        for node in node_records:
            node_id = str(node.get("node_id", ""))
            intent = str(node.get("intent_key", ""))
            proposed_slug = str(node.get("proposed_slug", ""))
            risk = str(node.get("risk_level", ""))
            minimum_sources = node.get("minimum_source_ids")
            review = str(node.get("review_requirement", ""))
            publication = str(node.get("publication_status", ""))

            if not ID_RE.fullmatch(node_id):
                findings.append(Finding("error", "invalid-node-id", cluster_id, node_id or None, "node_id must use lowercase dot or kebab notation."))
            if not SLUG_RE.fullmatch(intent):
                findings.append(Finding("error", "invalid-intent-key", cluster_id, node_id or None, "intent_key must use lowercase kebab-case."))
            if not SLUG_RE.fullmatch(proposed_slug):
                findings.append(Finding("error", "invalid-proposed-slug", cluster_id, node_id or None, "proposed_slug must use lowercase kebab-case."))

            for value, local_set, global_set, code in (
                (node_id, local_node_ids, global_node_ids, "duplicate-node-id"),
                (intent, local_intents, global_intents, "duplicate-intent"),
                (proposed_slug, local_slugs, global_proposed_slugs, "duplicate-proposed-slug"),
            ):
                if value in local_set or value in global_set:
                    findings.append(Finding("error", code, cluster_id, node_id or None, f"Duplicate value: {value}."))
                local_set.add(value)
                global_set.add(value)

            required_sources = 0
            if risk == "moderate":
                required_sources = int(policy.get("published_moderate_minimum_sources", 1))
            elif risk == "high":
                required_sources = int(policy.get("published_high_minimum_sources", 2))
            elif risk not in {"low", "moderate", "high", "critical"}:
                findings.append(Finding("error", "invalid-risk-level", cluster_id, node_id or None, f"Unsupported risk_level: {risk!r}."))
            if not isinstance(minimum_sources, int) or minimum_sources < required_sources:
                findings.append(Finding("error", "insufficient-source-plan", cluster_id, node_id or None, f"minimum_source_ids must be at least {required_sources} for {risk} risk."))
            if risk in {"high", "critical"} and review in {"", "unreviewed", "needs-specialist-review"}:
                findings.append(Finding("error", "insufficient-review-plan", cluster_id, node_id or None, "High-risk cluster nodes require a completed review target before publication."))
            if publication != "not-published":
                findings.append(Finding("error", "premature-publication-claim", cluster_id, node_id or None, "Registry planning nodes must remain not-published until content and evidence are reviewed."))

            legacy_paths = node.get("legacy_paths", [])
            if not isinstance(legacy_paths, list) or not legacy_paths:
                findings.append(Finding("error", "missing-legacy-path", cluster_id, node_id or None, "Each migration node must identify at least one legacy path."))
                continue
            for path in legacy_paths:
                match = LEGACY_CONCEPT_RE.fullmatch(str(path))
                if not match:
                    findings.append(Finding("error", "invalid-legacy-path", cluster_id, node_id or None, f"Invalid legacy concept path: {path!r}."))
                    continue
                number = int(match.group(1))
                if not (expected_start <= number <= expected_end):
                    findings.append(Finding("error", "legacy-path-outside-domain", cluster_id, node_id or None, f"Legacy concept {number} is outside cluster range."))
                if number in assigned_numbers:
                    findings.append(Finding("error", "duplicate-legacy-assignment", cluster_id, node_id or None, f"Legacy concept {number} is assigned to multiple nodes."))
                assigned_numbers.add(number)

        declared_unassigned = cluster.get("unassigned_legacy_concepts", [])
        expected_unassigned = sorted(set(range(expected_start, expected_end + 1)) - assigned_numbers)
        if declared_unassigned != expected_unassigned:
            findings.append(Finding("error", "unassigned-concept-mismatch", cluster_id, None, f"Expected unassigned legacy concepts {expected_unassigned}, found {declared_unassigned}."))

        gate = cluster.get("migration_gate", {})
        required_gates = {
            "requires_page_inventory_review",
            "requires_source_contract",
            "requires_unique_intent_review",
            "requires_internal_link_plan",
            "requires_redirect_map_review",
            "requires_full_ci_before_any_canonical_change",
        }
        missing_gates = sorted(key for key in required_gates if gate.get(key) is not True)
        if missing_gates:
            findings.append(Finding("error", "incomplete-migration-gate", cluster_id, None, f"Migration gates must be true: {', '.join(missing_gates)}."))

    errors = [item.as_dict() for item in findings if item.severity == "error"]
    warnings = [item.as_dict() for item in findings if item.severity == "warning"]
    return {
        "version": "160-topic-clusters",
        "clusters": len(clusters),
        "nodes": sum(1 + len(cluster.get("nodes", [])) for cluster in clusters),
        "legacy_concepts_mapped": sum(
            len(node.get("legacy_paths", []))
            for cluster in clusters
            for node in ([cluster.get("pillar", {})] + list(cluster.get("nodes", [])))
        ),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "policy": {
            "advisory_and_planning_only": True,
            "automatic_url_changes": False,
            "automatic_content_generation": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate semantic topic cluster plans against the legacy v8 generator.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--output", default="artifacts/topic-clusters-v160.json")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    registry = json.loads((root / "data" / "topic-cluster-registry-v160.json").read_text(encoding="utf-8"))
    domains = extract_literal_assignment(root / "scripts" / "scale_site_v8.py", "DOMAINS")
    facets = extract_literal_assignment(root / "scripts" / "scale_site_v8.py", "FACETS")
    report = validate_registry(registry, domains, facets)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("clusters", "nodes", "legacy_concepts_mapped", "error_count", "warning_count")}, ensure_ascii=False, indent=2))
    if report["error_count"]:
        raise SystemExit("\n".join(item["message"] for item in report["errors"][:80]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
