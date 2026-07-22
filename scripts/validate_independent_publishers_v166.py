import argparse
import json
from pathlib import Path


REQUIRED_PUBLISHER_KEYS = {
    "id",
    "issue",
    "name_ar",
    "content_path",
    "route_prefix",
    "allowed_content_types",
    "initial_priority",
}
REQUIRED_QUEUE_ITEM_KEYS = {
    "id",
    "title",
    "slug",
    "status",
    "search_intent",
    "audience",
    "age_group",
    "risk_level",
    "target_content_type",
    "required_sources",
    "acceptance",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root: Path):
    errors = []
    warnings = []
    registry_path = root / "data" / "independent-publishers-v166.json"
    if not registry_path.is_file():
        return {"errors": ["missing_registry"], "warnings": [], "publishers": []}

    registry = load_json(registry_path)
    publishers = registry.get("publishers", [])
    if len(publishers) != 10:
        errors.append(f"publisher_count:{len(publishers)}")

    if registry.get("operating_model", {}).get("mode") != "independent-end-to-end-publishers":
        errors.append("invalid_operating_mode")
    required_stages = registry.get("required_stages", [])
    for stage in [
        "topic-selection",
        "source-research",
        "draft",
        "seo-and-metadata",
        "automated-tests",
        "deployment",
        "live-sha-verification",
        "publication-log",
    ]:
        if stage not in required_stages:
            errors.append(f"missing_stage:{stage}")

    allowed_statuses = set(registry.get("queue_statuses", []))
    ids = set()
    issues = set()
    paths = set()
    routes = set()
    global_item_ids = set()
    global_slugs = set()
    publisher_reports = []

    for publisher in publishers:
        missing = REQUIRED_PUBLISHER_KEYS - set(publisher)
        if missing:
            errors.append(f"publisher_missing_keys:{publisher.get('id')}:{','.join(sorted(missing))}")
            continue

        publisher_id = publisher["id"]
        if publisher_id in ids:
            errors.append(f"duplicate_publisher_id:{publisher_id}")
        ids.add(publisher_id)

        issue = publisher["issue"]
        if issue in issues:
            errors.append(f"duplicate_issue:{issue}")
        issues.add(issue)

        content_path = publisher["content_path"]
        route_prefix = publisher["route_prefix"]
        if content_path in paths:
            errors.append(f"duplicate_content_path:{content_path}")
        paths.add(content_path)
        if route_prefix in routes:
            errors.append(f"duplicate_route_prefix:{route_prefix}")
        routes.add(route_prefix)
        if not route_prefix.startswith("/") or not route_prefix.endswith("/"):
            errors.append(f"invalid_route_prefix:{publisher_id}")

        queue_path = root / content_path / "queue.json"
        if not queue_path.is_file():
            errors.append(f"missing_queue:{publisher_id}")
            continue
        queue = load_json(queue_path)
        if queue.get("publisher_id") != publisher_id:
            errors.append(f"queue_publisher_mismatch:{publisher_id}")
        if queue.get("issue") != issue:
            errors.append(f"queue_issue_mismatch:{publisher_id}")
        if queue.get("route_prefix") != route_prefix:
            errors.append(f"queue_route_mismatch:{publisher_id}")

        items = queue.get("items", [])
        if not items:
            errors.append(f"empty_queue:{publisher_id}")
        local_ids = set()
        local_slugs = set()
        for item in items:
            missing_item = REQUIRED_QUEUE_ITEM_KEYS - set(item)
            if missing_item:
                errors.append(f"item_missing_keys:{publisher_id}:{','.join(sorted(missing_item))}")
                continue
            item_id = item["id"]
            slug = item["slug"]
            if item_id in local_ids or item_id in global_item_ids:
                errors.append(f"duplicate_item_id:{item_id}")
            local_ids.add(item_id)
            global_item_ids.add(item_id)
            if slug in local_slugs or slug in global_slugs:
                errors.append(f"duplicate_slug:{slug}")
            local_slugs.add(slug)
            global_slugs.add(slug)
            if item["status"] not in allowed_statuses:
                errors.append(f"invalid_status:{publisher_id}:{item['status']}")
            if item["target_content_type"] not in publisher["allowed_content_types"]:
                errors.append(f"content_type_outside_publisher:{publisher_id}:{item['target_content_type']}")
            if not item["required_sources"]:
                errors.append(f"missing_required_sources:{item_id}")
            if len(item["acceptance"]) < 3:
                errors.append(f"weak_acceptance:{item_id}")
            if item["status"] == "published":
                warnings.append(f"published_item_requires_separate_live_evidence:{item_id}")

        publisher_reports.append({
            "publisher_id": publisher_id,
            "issue": issue,
            "content_path": content_path,
            "route_prefix": route_prefix,
            "queue_items": len(items),
        })

    expected_issues = set(range(96, 106))
    if issues != expected_issues:
        errors.append(f"issue_set_mismatch:{sorted(issues)}")

    return {
        "schema_version": "1.0.0",
        "contract_id": registry.get("contract_id"),
        "publisher_count": len(publishers),
        "queue_item_count": len(global_item_ids),
        "errors": sorted(errors),
        "warnings": sorted(warnings),
        "publishers": publisher_reports,
    }


def main():
    parser = argparse.ArgumentParser(description="Validate ten independent end-to-end publishing workstreams.")
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate(args.root.resolve())
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    if report["errors"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
