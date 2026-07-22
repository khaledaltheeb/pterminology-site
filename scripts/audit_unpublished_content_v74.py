#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

TEXT_EXTENSIONS = {'.py', '.json', '.js', '.mjs', '.css', '.html', '.md', '.yml', '.yaml', '.txt', '.webmanifest'}
CONTENT_EXTENSIONS = {'.json', '.html', '.md'}
ASSET_EXTENSIONS = {'.js', '.mjs', '.css'}
IGNORE_PARTS = {'.git', '_site', 'node_modules', '__pycache__', '.pytest_cache', '_audit'}
DIRECT_PATH_RE = re.compile(r'(?P<path>(?:\.?\.?/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.(?:py|json|js|css|html|md|yml|yaml|mjs|webmanifest))')
GLOB_RE = re.compile(r'(?P<glob>(?:\.?\.?/)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.*?\[\]-]+)+\.(?:py|json|js|css|html|md|yml|yaml|mjs))')
PATH_CHAIN_RE = re.compile(r'(?P<root>ROOT|SITE|[A-Z][A-Z0-9_]*)\s*(?P<chain>(?:\s*/\s*[\'\"][^\'\"]+[\'\"]){2,})')
PATH_PART_RE = re.compile(r'/\s*[\'\"]([^\'\"]+)[\'\"]')


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(root: Path) -> list[Path]:
    result = []
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        if any(part in IGNORE_PARTS for part in path.relative_to(root).parts):
            continue
        result.append(path.resolve())
    return sorted(result)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return ''


def resolve_reference(root: Path, source: Path, raw: str) -> Path | None:
    value = raw.strip().strip('\'"').split('#', 1)[0].split('?', 1)[0]
    if not value or value.startswith(('http://', 'https://', 'data:', 'mailto:', 'tel:')):
        return None
    candidate = ((source.parent / value) if value.startswith('.') else (root / value.lstrip('/'))).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def expand_glob(root: Path, source: Path, raw: str) -> set[Path]:
    value = raw.strip().strip('\'"')
    if not any(token in value for token in ('*', '?', '[')):
        return set()
    relative_value = value.lstrip('/')
    base = source.parent if relative_value.startswith('.') else root
    result = set()
    try:
        candidates = base.glob(relative_value)
        for path in candidates:
            if not path.is_file():
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            result.add(resolved)
    except (NotImplementedError, ValueError, OSError):
        return set()
    return result


def references_from_file(root: Path, source: Path, text: str) -> set[Path]:
    found: set[Path] = set()
    for match in DIRECT_PATH_RE.finditer(text):
        target = resolve_reference(root, source, match.group('path'))
        if target:
            found.add(target)
    for match in GLOB_RE.finditer(text):
        found.update(expand_glob(root, source, match.group('glob')))
    for match in PATH_CHAIN_RE.finditer(text):
        parts = PATH_PART_RE.findall(match.group('chain'))
        if parts:
            target = resolve_reference(root, source, '/'.join(parts))
            if target:
                found.add(target)
    return found


def workflow_roots(root: Path) -> list[Path]:
    directory = root / '.github' / 'workflows'
    if not directory.is_dir():
        raise SystemExit('Missing .github/workflows')
    roots: list[Path] = []
    for path in sorted(directory.glob('*.y*ml')):
        text = read_text(path)
        lower = text.lower()
        name_match = re.search(r'^name:\s*(.+)$', lower, re.MULTILINE)
        name = name_match.group(1).strip() if name_match else path.name.lower()
        signals = (
            'validate every assessment and cognitive tool' in name,
            'deploy psychology platform' in name,
            'deploy validated' in name,
            'upload-pages-artifact' in lower,
            'stamp_deployment' in lower,
            'publish_daily_tools' in lower and '_site' in lower,
        )
        if any(signals):
            roots.append(path.resolve())
    known = (directory / 'validate-all-labs-v22.yml').resolve()
    if known.is_file() and known not in roots:
        roots.append(known)
    if not roots:
        raise SystemExit('No production workflow roots detected')
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


def extract_metadata(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != '.json':
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        return {'json_error': str(exc)}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, Any] = {}
    for key in ('version', 'language', 'status', 'review_status', 'updated_at', 'reviewed_at'):
        if key in payload:
            result[key] = payload[key]
    for key in ('title', 'name', 'heading'):
        if payload.get(key):
            result['title'] = payload[key]
            break
    for collection in ('guides', 'tools', 'paths', 'courses', 'modules', 'entries', 'items'):
        values = payload.get(collection)
        if isinstance(values, list):
            result[f'{collection}_count'] = len(values)
            if values and isinstance(values[0], dict):
                for key in ('title', 'name', 'heading'):
                    if values[0].get(key):
                        result.setdefault('title', values[0][key])
                        break
                for key in ('review_status', 'status', 'reviewed_at'):
                    if values[0].get(key):
                        result.setdefault(key, values[0][key])
    return result


def classify(path: Path, path_rel: str, metadata: dict[str, Any], referenced_by: list[str]) -> tuple[str, str]:
    status = str(metadata.get('review_status', metadata.get('status', ''))).lower()
    sensitive = ('medical', 'clinical', 'emergency', 'crisis', 'medication', 'down-syndrome', 'autism', 'adhd')
    if any(token in path_rel.lower() for token in sensitive) and 'needs' in status:
        return 'blocked-review', 'Health-sensitive source declares that specialist or external review is still needed'
    if path_rel.startswith('content/'):
        if referenced_by:
            return 'source-only', 'Referenced in the repository but unreachable from the production workflow graph'
        return 'unwired-content', 'Content source is not referenced by production or another source file'
    if path_rel.startswith('scripts/publish_'):
        return 'unwired-publisher', 'Publisher exists but is not reachable from production workflows'
    if path_rel.startswith('assets/'):
        return 'unwired-asset', 'Runtime asset is not reachable from production workflows'
    if path_rel.startswith('docs/') or path.suffix.lower() == '.md':
        return 'documentation-only', 'Documentation source is not part of the published site artifact'
    if path_rel.startswith('data/'):
        return 'governance-data-only', 'Machine-readable governance data is not part of a public route'
    return 'unreachable-source', 'Source is not reachable from production workflows'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default='.')
    parser.add_argument('--out', default='_audit/unpublished-content-v74.json')
    parser.add_argument('--markdown', default='_audit/unpublished-content-v74.md')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    files = iter_files(root)
    roots = workflow_roots(root)
    reachable, graph = reachable_graph(root, roots)
    references = all_reference_locations(root, files)

    content = [p for p in files if p.suffix.lower() in CONTENT_EXTENSIONS and p.relative_to(root).parts[0] in {'content', 'data', 'docs'}]
    publishers = [p for p in files if rel(root, p).startswith('scripts/publish_') and p.suffix == '.py']
    assets = [p for p in files if rel(root, p).startswith('assets/') and p.suffix.lower() in ASSET_EXTENSIONS]
    candidates = []
    for path in sorted(set(content + publishers + assets)):
        if path in reachable:
            continue
        path_rel = rel(root, path)
        metadata = extract_metadata(path)
        referenced_by = references.get(path_rel, [])
        category, reason = classify(path, path_rel, metadata, referenced_by)
        candidates.append({'path': path_rel, 'category': category, 'reason': reason, 'referenced_by': referenced_by, 'metadata': metadata, 'bytes': path.stat().st_size})

    counts: dict[str, int] = defaultdict(int)
    for item in candidates:
        counts[item['category']] += 1
    report = {
        'version': 74,
        'repository_root': root.name,
        'production_workflow_roots': [rel(root, p) for p in roots],
        'source_file_count': len(files),
        'reachable_file_count': len(reachable),
        'content_source_count': len(content),
        'publisher_script_count': len(publishers),
        'asset_source_count': len(assets),
        'candidate_count': len(candidates),
        'category_counts': dict(sorted(counts.items())),
        'candidates': candidates,
        'reachable_files': sorted(rel(root, p) for p in reachable),
        'production_graph': graph,
    }
    out = (root / args.out).resolve()
    markdown = (root / args.markdown).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    priority = [item for item in candidates if item['category'] in {'unwired-content', 'source-only', 'unwired-publisher', 'unwired-asset', 'blocked-review'}]
    lines = ['# Unpublished content inventory v74', '', f"- Production roots: {', '.join(report['production_workflow_roots'])}", f"- Repository files scanned: {report['source_file_count']}", f"- Files reachable from production: {report['reachable_file_count']}", f"- Publication candidates: {report['candidate_count']}", '', '## Category counts', '']
    lines.extend(f"- `{category}`: {count}" for category, count in report['category_counts'].items())
    lines.extend(['', '## Priority candidates', ''])
    for item in priority:
        title = item['metadata'].get('title')
        suffix = f' — {title}' if title else ''
        lines.append(f"- `{item['path']}` — **{item['category']}**{suffix}: {item['reason']}")
    markdown.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'candidate_count': report['candidate_count'], 'category_counts': report['category_counts'], 'report': rel(root, out), 'markdown': rel(root, markdown)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
