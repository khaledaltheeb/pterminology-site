#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

TEXT_EXTENSIONS = {".py", ".json", ".js", ".mjs", ".css", ".html", ".md", ".yml", ".yaml", ".txt", ".webmanifest"}
CANDIDATE_ROOTS = {"content", "data", "docs", "assets", "scripts"}
IGNORE_PARTS = {".git", "_site", "node_modules", "__pycache__", ".pytest_cache", "_audit"}
DIRECT_PATH_RE = re.compile(r"(?P<path>(?:\.?\.?/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.(?:py|json|js|mjs|css|html|md|yml|yaml|txt|webmanifest))")
PATH_CHAIN_RE = re.compile(r"(?P<root>ROOT|SITE|[A-Z][A-Z0-9_]*)\s*(?P<chain>(?:\s*/\s*['\"][^'\"]+['\"]){2,})")
PATH_PART_RE = re.compile(r"/\s*['\"]([^'\"]+)['\"]")
RUN_PUBLISHER_RE = re.compile(r"\brun_publisher\(\s*['\"]([^'\"]+\.py)['\"]\s*\)")
STATUS_PATTERNS = (
    ("built-not-published", re.compile(r"\bbuilt-not-published\b", re.I)),
    ("prepared-not-published", re.compile(r"\bprepared-not-published\b", re.I)),
    ("not-published", re.compile(r"(?<!built-)(?<!prepared-)\bnot-published\b", re.I)),
    ("needs-specialist-review", re.compile(r"\bneeds-specialist-review\b", re.I)),
    ("needs-external-review", re.compile(r"\bneeds-external-review\b", re.I)),
    ("needs-review", re.compile(r"(?<!specialist-)(?<!external-)\bneeds-review\b", re.I)),
    ("internally-reviewed", re.compile(r"\binternally-reviewed\b", re.I)),
    ("published", re.compile(r"(?<!not-)\bpublished\b", re.I)),
)


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORE_PARTS for part in path.relative_to(root).parts):
            continue
        files.append(path.resolve())
    return sorted(files)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


def resolve_reference(root: Path, source: Path, raw: str) -> Path | None:
    value = raw.strip().strip("'\"").split("#", 1)[0].split("?", 1)[0]
    if not value or value.startswith(("http://", "https://", "data:", "mailto:", "tel:")):
        return None
    candidate = ((source.parent / value) if value.startswith(".") else (root / value.lstrip("/"))).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def references_from_file(root: Path, source: Path, text: str) -> set[Path]:
    found: set[Path] = set()
    for match in DIRECT_PATH_RE.finditer(text):
        target = resolve_reference(root, source, match.group("path"))
        if target:
            found.add(target)
    for match in PATH_CHAIN_RE.finditer(text):
        parts = PATH_PART_RE.findall(match.group("chain"))
        if parts:
            target = resolve_reference(root, source, "/".join(parts))
            if target:
                found.add(target)
    for match in RUN_PUBLISHER_RE.finditer(text):
        target = resolve_reference(root, source, "scripts/" + match.group(1))
        if target:
            found.add(target)
    return found


def workflow_roots(root: Path) -> list[Path]:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        raise SystemExit("Missing .github/workflows")
    roots: list[Path] = []
    for path in sorted(directory.glob("*.y*ml")):
        text = read_text(path)
        lower = text.lower()
        signals = (
            "upload-pages-artifact" in lower,
            "validated-production-site" in lower,
            "stamp_deployment" in lower,
            "deploy psychology platform" in lower,
            "validate every assessment and cognitive tool" in lower,
            "publish_daily_tools" in lower and "_site" in lower,
        )
        if any(signals):
            roots.append(path.resolve())
    known = (directory / "validate-all-labs-v22.yml").resolve()
    if known.is_file() and known not in roots:
        roots.append(known)
    if not roots:
        raise SystemExit("No production workflow roots detected")
    return sorted(set(roots))


def reachable_graph(root: Path, roots: Iterable[Path]) -> tuple[set[Path], dict[str, list[str]]]:
    reachable: set[Path] = set()
    edges: dict[str, list[str]] = defaultdict(list)
    queue = deque(path.resolve() for path in roots)
    while queue:
        source = queue.popleft()
        if source in reachable or not source.is_file():
            continue
        reachable.add(source)
        if source.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        for target in sorted(references_from_file(root, source, read_text(source))):
            edges[rel(root, source)].append(rel(root, target))
            if target not in reachable:
                queue.append(target)
    return reachable, {key: sorted(set(values)) for key, values in sorted(edges.items())}


def all_reference_locations(root: Path, files: Iterable[Path]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for source in files:
        if source.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        for target in references_from_file(root, source, read_text(source)):
            result[rel(root, target)].append(rel(root, source))
    return {key: sorted(set(values)) for key, values in sorted(result.items())}


def extract_metadata(path: Path, text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if path.suffix.lower() == ".json":
        try:
            payload = json.loads(text)
        except Exception as exc:
            return {"json_error": str(exc)}
        if isinstance(payload, dict):
            for key in ("version", "language", "status", "review_status", "publication_status", "updated_at", "reviewed_at", "title", "name", "heading"):
                if key in payload:
                    result[key] = payload[key]
            for collection in ("guides", "tools", "paths", "courses", "modules", "entries", "items"):
                values = payload.get(collection)
                if isinstance(values, list):
                    result[f"{collection}_count"] = len(values)
    statuses = [name for name, pattern in STATUS_PATTERNS if pattern.search(text)]
    if statuses:
        result["detected_status_tokens"] = statuses
    title_match = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    if title_match and "title" not in result:
        result["title"] = re.sub(r"\s+", " ", title_match.group(1)).strip()
    return result


def classify(path_rel: str, metadata: dict[str, Any], referenced_by: list[str], reachable: bool) -> tuple[str, str, str]:
    status_text = " ".join(str(value).lower() for value in metadata.values())
    needs_review = any(token in status_text for token in ("needs-specialist-review", "needs-external-review", "needs-review"))
    built_not_published = any(token in status_text for token in ("built-not-published", "prepared-not-published", "not-published"))
    if needs_review:
        return "blocked-review", "Source declares that specialist, external, or other required review is still outstanding", "do-not-publish"
    if reachable and built_not_published:
        return "wired-unconfirmed", "Source is wired to production but still declares a non-published state", "verify-live"
    if reachable:
        return "production-reachable", "Source is reachable from a detected production workflow", "retain"
    if path_rel.startswith("content/"):
        if referenced_by:
            return "source-only", "Referenced elsewhere but unreachable from the production workflow graph", "review-and-wire"
        return "unwired-content", "Content source is not referenced by production or another source file", "review-and-wire"
    if path_rel.startswith("scripts/publish_"):
        return "unwired-publisher", "Publisher exists but is not reachable from production workflows", "review-and-wire"
    if path_rel.startswith("assets/"):
        return "unwired-asset", "Runtime asset is not reachable from production workflows", "review-and-wire"
    if path_rel.startswith("docs/") or path_rel.endswith(".md"):
        return "documentation-only", "Documentation is not part of the published artifact", "document-only"
    if path_rel.startswith("data/"):
        return "governance-data-only", "Machine-readable governance data is not a public route", "retain-internal"
    return "unreachable-source", "Source is not reachable from production workflows", "manual-review"


def is_candidate(root: Path, path: Path) -> bool:
    parts = path.relative_to(root).parts
    if not parts or parts[0] not in CANDIDATE_ROOTS:
        return False
    if parts[0] == "scripts":
        return path.name.startswith("publish_") or path.name.startswith("apply_") or path.name.startswith("finalize_")
    if parts[0] == "assets":
        return path.suffix.lower() in {".js", ".mjs", ".css"}
    return path.suffix.lower() in {".json", ".html", ".md"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--out", default="_audit/unpublished-content-v201.json")
    parser.add_argument("--markdown", default="_audit/unpublished-content-v201.md")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = iter_files(root)
    roots = workflow_roots(root)
    reachable, graph = reachable_graph(root, roots)
    references = all_reference_locations(root, files)

    items: list[dict[str, Any]] = []
    for path in files:
        if not is_candidate(root, path):
            continue
        path_rel = rel(root, path)
        text = read_text(path)
        metadata = extract_metadata(path, text)
        referenced_by = references.get(path_rel, [])
        category, reason, action = classify(path_rel, metadata, referenced_by, path in reachable)
        items.append({
            "path": path_rel,
            "category": category,
            "recommended_action": action,
            "reason": reason,
            "reachable": path in reachable,
            "referenced_by": referenced_by,
            "metadata": metadata,
            "bytes": path.stat().st_size,
        })

    counts: dict[str, int] = defaultdict(int)
    actions: dict[str, int] = defaultdict(int)
    for item in items:
        counts[item["category"]] += 1
        actions[item["recommended_action"]] += 1
    priority_categories = {"blocked-review", "wired-unconfirmed", "source-only", "unwired-content", "unwired-publisher", "unwired-asset"}
    priority = [item for item in items if item["category"] in priority_categories]
    report = {
        "version": 201,
        "repository_root": root.name,
        "production_workflow_roots": [rel(root, path) for path in roots],
        "source_file_count": len(files),
        "reachable_file_count": len(reachable),
        "audited_item_count": len(items),
        "priority_item_count": len(priority),
        "category_counts": dict(sorted(counts.items())),
        "action_counts": dict(sorted(actions.items())),
        "priority_items": priority,
        "items": items,
        "reachable_files": sorted(rel(root, path) for path in reachable),
        "production_graph": graph,
    }
    out = (root / args.out).resolve()
    markdown = (root / args.markdown).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Unpublished and unwired content audit v201",
        "",
        f"- Repository files scanned: {len(files)}",
        f"- Files reachable from production: {len(reachable)}",
        f"- Audited content/publisher/asset items: {len(items)}",
        f"- Priority items: {len(priority)}",
        "",
        "## Category counts",
        "",
    ]
    lines.extend(f"- `{key}`: {value}" for key, value in sorted(counts.items()))
    lines.extend(["", "## Priority items", ""])
    for item in priority:
        title = item["metadata"].get("title") or item["metadata"].get("name") or ""
        suffix = f" — {title}" if title else ""
        lines.append(f"- `{item['path']}` — **{item['category']}** / `{item['recommended_action']}`{suffix}: {item['reason']}")
    markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "priority_item_count": len(priority),
        "category_counts": report["category_counts"],
        "action_counts": report["action_counts"],
        "report": rel(root, out),
        "markdown": rel(root, markdown),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
