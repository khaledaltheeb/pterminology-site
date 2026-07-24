#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

LEGACY_BLOG = 'href="/pterminology-site/blog/"'
MAGAZINE = 'href="/pterminology-site/magazine/"'
TARGETS = (
    "editorial-methodology/index.html",
    "evaluate-mental-health-information/index.html",
    "guides/source-citation-and-update-transparency/index.html",
)


def finalize(site: Path) -> dict[str, object]:
    changed_pages: list[str] = []
    missing_pages: list[str] = []
    remaining_legacy: list[str] = []

    for relative in TARGETS:
        path = site / relative
        if not path.is_file():
            missing_pages.append(relative)
            continue
        text = path.read_text(encoding="utf-8")
        updated = text.replace(LEGACY_BLOG, MAGAZINE)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed_pages.append(relative)
        if LEGACY_BLOG in updated:
            remaining_legacy.append(relative)

    if missing_pages:
        raise SystemExit(f"Missing generated trust-guide pages: {missing_pages}")
    if remaining_legacy:
        raise SystemExit(f"Legacy blog links remain in trust guides: {remaining_legacy}")

    report_path = site / "api" / "trust-guides-v201.json"
    if not report_path.is_file():
        raise SystemExit("Missing trust-guides-v201 report before link finalization")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["link_compatibility"] = {
        "legacy_blog_route": "/blog/",
        "active_route": "/magazine/",
        "changed_pages": changed_pages,
        "remaining_legacy_links": [],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    result = {
        "version": 201,
        "changed_pages": changed_pages,
        "remaining_legacy_links": [],
        "active_route": "/magazine/",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not target.is_dir():
        raise SystemExit(f"Missing site directory: {target}")
    finalize(target)
