from __future__ import annotations

import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA_FILES = [
    ROOT / "content/v18/care-guides-ar.json",
    ROOT / "content/v18/care-guides-adhd-ar.json",
    ROOT / "content/v18/care-guides-autism-ar.json",
]
BLOCKED_REVIEW_STATUSES = {"needs-specialist-review"}
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
SCHEMA_PATTERN = re.compile(
    r'(<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>)(.*?)(</script>)',
    re.IGNORECASE | re.DOTALL,
)
COMMENT_BLOCK_PATTERN = re.compile(
    r'<!--\s*(?P<marker>[A-Za-z0-9._-]+)\s*-->(?P<body>.*?)<!--\s*/(?P=marker)\s*-->',
    re.DOTALL,
)


def load_guides() -> list[dict]:
    guides: list[dict] = []
    for path in DATA_FILES:
        payload = json.loads(path.read_text(encoding="utf-8"))
        guides.extend(payload.get("guides", []))
    return guides


def blocked_guides() -> list[dict]:
    return [
        guide
        for guide in load_guides()
        if guide.get("review_status") in BLOCKED_REVIEW_STATUSES
    ]


def route_token(slug: str) -> str:
    return f"care-guides/{slug}/"


def prune_schema(value: object, tokens: tuple[str, ...]) -> object | None:
    if isinstance(value, list):
        cleaned = []
        for item in value:
            pruned = prune_schema(item, tokens)
            if pruned is not None:
                cleaned.append(pruned)
        return cleaned
    if isinstance(value, dict):
        route_fields = ("url", "item", "mainEntityOfPage", "@id")
        for field in route_fields:
            candidate = value.get(field)
            if isinstance(candidate, str) and any(token in candidate for token in tokens):
                return None
        cleaned: dict[str, object] = {}
        for key, item in value.items():
            pruned = prune_schema(item, tokens)
            if pruned is not None:
                cleaned[key] = pruned
        return cleaned
    return value


def cleanse_schema(text: str, tokens: tuple[str, ...]) -> tuple[str, int]:
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        raw = match.group(2)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return match.group(0)
        cleaned = prune_schema(payload, tokens)
        if cleaned == payload:
            return match.group(0)
        changed += 1
        return match.group(1) + json.dumps(cleaned, ensure_ascii=False) + match.group(3)

    return SCHEMA_PATTERN.sub(replace, text), changed


def remove_blocked_references(text: str, tokens: tuple[str, ...]) -> tuple[str, int]:
    removed = 0

    def remove_comment_block(match: re.Match[str]) -> str:
        nonlocal removed
        if any(token in match.group("body") for token in tokens):
            removed += 1
            return ""
        return match.group(0)

    text = COMMENT_BLOCK_PATTERN.sub(remove_comment_block, text)
    token_pattern = "|".join(re.escape(token) for token in tokens)
    for tag in ("article", "section", "li", "p"):
        pattern = re.compile(
            rf"<{tag}\b[^>]*>.*?(?:{token_pattern}).*?</{tag}>",
            re.IGNORECASE | re.DOTALL,
        )
        text, count = pattern.subn("", text)
        removed += count
    anchor_pattern = re.compile(
        rf"<a\b[^>]*href=[\"'][^\"']*(?:{token_pattern})[^\"']*[\"'][^>]*>.*?</a>",
        re.IGNORECASE | re.DOTALL,
    )
    text, count = anchor_pattern.subn("", text)
    removed += count
    text, schema_changes = cleanse_schema(text, tokens)
    removed += schema_changes
    return text, removed


def remove_sitemap_entries(tokens: tuple[str, ...]) -> int:
    removed = 0
    for path in SITE.glob("sitemap*.xml"):
        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise SystemExit(f"Invalid sitemap XML during health gate: {path.name}: {exc}") from exc
        root = tree.getroot()
        changed = False
        for parent in root.iter():
            for child in list(parent):
                loc = child.find("{*}loc")
                if loc is None or not loc.text:
                    continue
                if any(token in loc.text for token in tokens):
                    parent.remove(child)
                    removed += 1
                    changed = True
        if changed:
            tree.write(path, encoding="utf-8", xml_declaration=True)
    return removed


def sitemap_url_count(path: Path) -> int:
    if not path.is_file():
        raise SystemExit(f"Missing sitemap after health publication gate: {path.name}")
    return len(ET.parse(path).getroot().findall("{*}url"))


def update_reports(blocked: list[dict], removed_links: int, removed_sitemaps: int) -> dict:
    blocked_slugs = [guide["slug"] for guide in blocked]
    care_root = SITE / "care-guides"
    page_count = len(list(care_root.rglob("index.html")))
    sitemap_count = sitemap_url_count(SITE / "sitemap-care-guides.xml")
    if page_count != sitemap_count:
        raise SystemExit(
            f"Health gate page/sitemap mismatch: pages={page_count}, sitemap_urls={sitemap_count}"
        )

    care_report_path = SITE / "api" / "care-guides-v21.json"
    care_report = json.loads(care_report_path.read_text(encoding="utf-8"))
    care_report.update(
        {
            "publication_gate_version": 192,
            "guides": max(0, sitemap_count - 1),
            "pages": page_count,
            "sitemap_urls": sitemap_count,
            "blocked_review_guides": len(blocked_slugs),
            "blocked_review_slugs": blocked_slugs,
            "needs_specialist_review_published": False,
            "autism_published": "autism-family-practical-guide" not in blocked_slugs,
        }
    )
    care_report_path.write_text(
        json.dumps(care_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    journey_path = SITE / "api" / "care-guides-homepage-v21.json"
    if journey_path.is_file():
        journey = json.loads(journey_path.read_text(encoding="utf-8"))
        for key in list(journey):
            if key.startswith("autism_inbound_") or key.startswith("autism_outgoing_"):
                journey[key] = False
        journey["publication_gate_version"] = 192
        journey["blocked_review_slugs"] = blocked_slugs
        journey["blocked_review_links_removed"] = True
        journey["no_blocked_review_routes"] = True
        journey.setdefault("changed", {})["health_publication_gate"] = True
        journey_path.write_text(
            json.dumps(journey, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    report = {
        "version": 192,
        "status": "passed",
        "blocked_review_statuses": sorted(BLOCKED_REVIEW_STATUSES),
        "blocked_guides": len(blocked_slugs),
        "blocked_slugs": blocked_slugs,
        "blocked_pages_absent": True,
        "blocked_links_removed": removed_links,
        "blocked_sitemap_entries_removed": removed_sitemaps,
        "remaining_blocked_routes": [],
        "care_guide_pages": page_count,
        "care_guide_sitemap_urls": sitemap_count,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "health-publication-gate-v192.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def enforce() -> dict:
    if not SITE.is_dir():
        raise SystemExit(f"Missing production output for health gate: {SITE}")
    blocked = blocked_guides()
    tokens = tuple(route_token(guide["slug"]) for guide in blocked)
    removed_pages = 0
    for guide in blocked:
        target = SITE / "care-guides" / guide["slug"]
        if target.exists():
            shutil.rmtree(target)
            removed_pages += 1

    removed_links = 0
    if tokens:
        for path in SITE.rglob("*.html"):
            text = path.read_text(encoding="utf-8")
            cleaned, count = remove_blocked_references(text, tokens)
            if cleaned != text:
                path.write_text(cleaned, encoding="utf-8")
            removed_links += count
    removed_sitemaps = remove_sitemap_entries(tokens) if tokens else 0

    remaining: list[str] = []
    for token in tokens:
        blocked_dir = SITE / token.rstrip("/")
        if blocked_dir.exists():
            remaining.append(str(blocked_dir.relative_to(SITE)))
        for path in SITE.rglob("*.html"):
            if token in path.read_text(encoding="utf-8"):
                remaining.append(str(path.relative_to(SITE)))
        for path in SITE.glob("sitemap*.xml"):
            if token in path.read_text(encoding="utf-8"):
                remaining.append(path.name)
    if remaining:
        raise SystemExit(f"Blocked specialist-review routes remain in production: {sorted(set(remaining))}")

    report = update_reports(blocked, removed_links, removed_sitemaps)
    report["blocked_pages_removed"] = removed_pages
    report_path = SITE / "api" / "health-publication-gate-v192.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    print(json.dumps(enforce(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
