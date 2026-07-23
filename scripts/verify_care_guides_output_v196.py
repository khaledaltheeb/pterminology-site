from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
REPORT_PATH = SITE / "api" / "care-guides-output-contract-v196.json"


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing report: {path.relative_to(SITE)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid JSON: {path.relative_to(SITE)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"report must be an object: {path.relative_to(SITE)}")
        return {}
    return value


def count_sitemap_urls(path: Path, errors: list[str]) -> int:
    if not path.is_file():
        errors.append(f"missing sitemap: {path.relative_to(SITE)}")
        return 0
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        errors.append(f"invalid sitemap XML: {path.relative_to(SITE)}: {exc}")
        return 0
    return len(root.findall("{*}url"))


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> None:
    errors: list[str] = []
    page_results: list[dict[str, Any]] = []
    report = load_json(SITE / "api" / "care-guides-v21.json", errors)
    linked = load_json(SITE / "api" / "care-guides-homepage-v21.json", errors)
    gate = load_json(SITE / "api" / "health-publication-gate-v192.json", errors)

    expected_guides = int(report.get("guides", -1))
    expected_pages = int(report.get("pages", -1))
    expected_urls = int(report.get("sitemap_urls", -1))
    actual_pages = sum(1 for _ in (SITE / "care-guides").rglob("index.html")) if (SITE / "care-guides").is_dir() else 0
    sitemap_path = SITE / "sitemap-care-guides.xml"
    actual_urls = count_sitemap_urls(sitemap_path, errors)

    check(expected_guides >= 1, f"no published guides: {report}", errors)
    check(expected_pages == expected_guides + 1, f"page count contract: guides={expected_guides}, pages={expected_pages}", errors)
    check(expected_urls == expected_pages, f"sitemap report contract: urls={expected_urls}, pages={expected_pages}", errors)
    check(actual_pages == expected_pages, f"generated page mismatch: actual={actual_pages}, expected={expected_pages}", errors)
    check(actual_urls == expected_urls, f"generated sitemap mismatch: actual={actual_urls}, expected={expected_urls}", errors)
    check(report.get("all_have_sources") is True, "care-guide source coverage is false", errors)
    check(report.get("all_have_unique_titles") is True, "care-guide title uniqueness is false", errors)
    check(report.get("needs_specialist_review_published") is False, "specialist-review content was published", errors)
    check(gate.get("status") == "passed", f"health publication gate did not pass: {gate}", errors)
    check(not gate.get("remaining_blocked_routes", []), f"blocked routes remain: {gate.get('remaining_blocked_routes')}", errors)
    check(linked.get("care_guides_linked") is True, f"care-guide discovery link missing: {linked}", errors)
    check(linked.get("navigation_link") is True, f"care-guide navigation link missing: {linked}", errors)
    check(linked.get("hero_link") is True, f"care-guide hero link missing: {linked}", errors)

    root_sitemap = SITE / "sitemap.xml"
    check(root_sitemap.is_file(), "root sitemap missing", errors)
    if root_sitemap.is_file():
        check("sitemap-care-guides.xml" in root_sitemap.read_text(encoding="utf-8"), "care-guide sitemap not registered", errors)
    homepage = SITE / "index.html"
    check(homepage.is_file(), "homepage missing", errors)
    if homepage.is_file():
        check('href="care-guides/"' in homepage.read_text(encoding="utf-8"), "homepage care-guide link missing", errors)

    pages = sorted((SITE / "care-guides").glob("*/index.html")) if (SITE / "care-guides").is_dir() else []
    check(len(pages) == expected_guides, f"child guide count mismatch: actual={len(pages)}, expected={expected_guides}", errors)
    titles: dict[str, str] = {}
    descriptions: dict[str, str] = {}

    for page in pages:
        rel = str(page.relative_to(SITE))
        text = page.read_text(encoding="utf-8")
        result = {
            "path": rel,
            "h1_count": text.count("<h1>"),
            "json_ld": "application/ld+json" in text,
            "article_schema": "Article" in text,
            "howto_schema": "HowTo" in text,
            "institutional_sources": "مصادر مؤسسية للمراجعة" in text,
            "urgent_help": "خدمات الطوارئ المحلية" in text or "مساعدة عاجلة" in text,
        }
        title_match = re.search(r"<title>(.*?)</title>", text, re.S)
        desc_match = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
        result["title"] = title_match.group(1).strip() if title_match else None
        result["description"] = desc_match.group(1).strip() if desc_match else None
        page_errors: list[str] = []
        check(result["h1_count"] == 1, f"{rel}: expected one H1, found {result['h1_count']}", page_errors)
        check(result["json_ld"], f"{rel}: JSON-LD missing", page_errors)
        check(result["article_schema"], f"{rel}: Article schema missing", page_errors)
        check(result["howto_schema"], f"{rel}: HowTo schema missing", page_errors)
        check(result["institutional_sources"], f"{rel}: visible institutional sources missing", page_errors)
        check(result["urgent_help"], f"{rel}: urgent-help language missing", page_errors)
        check(result["title"] is not None, f"{rel}: title missing", page_errors)
        check(result["description"] is not None, f"{rel}: meta description missing", page_errors)
        if result["title"]:
            previous = titles.get(str(result["title"]))
            check(previous is None, f"{rel}: duplicate title also used by {previous}: {result['title']}", page_errors)
            titles[str(result["title"])] = rel
        if result["description"]:
            previous = descriptions.get(str(result["description"]))
            check(previous is None, f"{rel}: duplicate description also used by {previous}", page_errors)
            descriptions[str(result["description"])] = rel
        result["errors"] = page_errors
        errors.extend(page_errors)
        page_results.append(result)

    output = {
        "version": 196,
        "status": "passed" if not errors else "failed",
        "expected_guides": expected_guides,
        "expected_pages": expected_pages,
        "expected_sitemap_urls": expected_urls,
        "actual_pages": actual_pages,
        "actual_sitemap_urls": actual_urls,
        "blocked_review_slugs": report.get("blocked_review_slugs", []),
        "unique_titles": len(titles),
        "unique_descriptions": len(descriptions),
        "pages": page_results,
        "errors": errors,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(f"care-guide output contract failed with {len(errors)} error(s)")


if __name__ == "__main__":
    main()
