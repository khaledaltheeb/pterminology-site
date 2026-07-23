#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

BASE_PATH = "/pterminology-site/"
SECTION_PREFIXES = {
    "home": "/",
    "encyclopedia": "/encyclopedia/",
    "blog": "/blog/",
    "special_needs": "/special-needs/",
    "care_guides": "/care-guides/",
    "assessments": "/assessment-lab/",
    "cognitive": "/cognitive-lab/",
    "family": "/sectors/family/",
    "trust": "/trust/",
}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.canonical = ""
        self.h1 = 0
        self.json_ld = 0
        self.links: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = {key.lower(): (value or "") for key, value in attrs}
        tag = tag.lower()
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and data.get("name", "").lower() == "description":
            self.description = data.get("content", "").strip()
        elif tag == "link" and "canonical" in data.get("rel", "").lower().split():
            self.canonical = data.get("href", "").strip()
        elif tag == "h1":
            self.h1 += 1
        elif tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self.json_ld += 1
        elif tag == "a" and data.get("href"):
            self.links.append(data["href"].strip())

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def normalize_route(site: Path, html_file: Path) -> str:
    rel = html_file.relative_to(site).as_posix()
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[:-10]
    return "/" + rel


def normalize_internal_href(href: str, current_route: str) -> str | None:
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlparse(href)
    if parsed.scheme and parsed.netloc:
        if "khaledaltheeb.github.io" not in parsed.netloc:
            return None
        path = parsed.path
    else:
        path = parsed.path
    if path.startswith(BASE_PATH):
        path = "/" + path[len(BASE_PATH):]
    elif not path.startswith("/"):
        parent = current_route if current_route.endswith("/") else current_route.rsplit("/", 1)[0] + "/"
        path = parent + path
    path = re.sub(r"/{2,}", "/", path)
    if path.endswith("index.html"):
        path = path[:-10]
    if path and not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path += "/"
    return path or "/"


def section_for(route: str) -> str:
    if route == "/":
        return "home"
    for name, prefix in SECTION_PREFIXES.items():
        if name != "home" and route.startswith(prefix):
            return name
    return "other"


def audit(site: Path) -> dict:
    pages: dict[str, dict] = {}
    for html_file in sorted(site.rglob("*.html")):
        parser = PageParser()
        parser.feed(html_file.read_text(encoding="utf-8", errors="replace"))
        route = normalize_route(site, html_file)
        links = [item for href in parser.links if (item := normalize_internal_href(href, route))]
        pages[route] = {
            "route": route,
            "file": html_file.relative_to(site).as_posix(),
            "section": section_for(route),
            "title": parser.title.strip(),
            "description": parser.description,
            "canonical": parser.canonical,
            "h1_count": parser.h1,
            "json_ld_count": parser.json_ld,
            "outgoing_internal": sorted(set(links)),
        }

    incoming: dict[str, set[str]] = defaultdict(set)
    broken: dict[str, list[str]] = defaultdict(list)
    for source, page in pages.items():
        for target in page["outgoing_internal"]:
            if target in pages:
                incoming[target].add(source)
            elif not target.startswith(("/assets/", "/api/")):
                broken[source].append(target)

    rows = []
    severity_counts = Counter()
    for route, page in pages.items():
        issues: list[str] = []
        incoming_count = len(incoming.get(route, set()))
        cross_sections = sorted({section_for(source) for source in incoming.get(route, set()) if section_for(source) != page["section"]})
        if route != "/" and incoming_count == 0:
            issues.append("orphan")
        if route != "/" and incoming_count < 2:
            issues.append("weak_incoming_links")
        if route != "/" and not cross_sections:
            issues.append("no_cross_section_discovery")
        if len(page["title"]) < 20:
            issues.append("weak_title")
        if not 80 <= len(page["description"]) <= 180:
            issues.append("weak_meta_description")
        if page["h1_count"] != 1:
            issues.append("invalid_h1_count")
        if not page["canonical"]:
            issues.append("missing_canonical")
        if page["json_ld_count"] == 0:
            issues.append("missing_json_ld")
        if broken.get(route):
            issues.append("broken_internal_links")
        severity = "critical" if any(item in issues for item in ("broken_internal_links", "missing_canonical", "invalid_h1_count")) else "improve" if issues else "pass"
        severity_counts[severity] += 1
        rows.append({
            **page,
            "incoming_count": incoming_count,
            "incoming_sections": cross_sections,
            "broken_targets": sorted(set(broken.get(route, []))),
            "issues": issues,
            "decision": "fix-before-publish" if severity == "critical" else "improve" if issues else "pass",
            "severity": severity,
        })

    rows.sort(key=lambda row: ({"critical": 0, "improve": 1, "pass": 2}[row["severity"]], row["incoming_count"], row["route"]))
    return {
        "version": 177,
        "site": str(site),
        "page_count": len(rows),
        "summary": dict(severity_counts),
        "section_counts": dict(Counter(row["section"] for row in rows)),
        "orphan_count": sum("orphan" in row["issues"] for row in rows),
        "weak_discovery_count": sum("no_cross_section_discovery" in row["issues"] for row in rows),
        "broken_source_count": sum(bool(row["broken_targets"]) for row in rows),
        "pages": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--csv", dest="csv_path", type=Path, required=True)
    args = parser.parse_args()
    if not args.site.is_dir():
        raise SystemExit(f"Site directory does not exist: {args.site}")
    report = audit(args.site.resolve())
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.csv_path.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["severity", "decision", "section", "route", "incoming_count", "incoming_sections", "issues", "broken_targets", "title", "description", "canonical"])
        writer.writeheader()
        for row in report["pages"]:
            writer.writerow({
                **{key: row[key] for key in ("severity", "decision", "section", "route", "incoming_count", "title", "description", "canonical")},
                "incoming_sections": "|".join(row["incoming_sections"]),
                "issues": "|".join(row["issues"]),
                "broken_targets": "|".join(row["broken_targets"]),
            })
    print(json.dumps({key: report[key] for key in ("version", "page_count", "summary", "orphan_count", "weak_discovery_count", "broken_source_count")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
