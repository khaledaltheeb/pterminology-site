from __future__ import annotations

import json
import posixpath
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

BASE_HOST = "khaledaltheeb.github.io"
BASE_PATH = "/pterminology-site/"
VERIFICATION_PATTERN = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.IGNORECASE,
)
EXCLUDED_ORPHAN_PATHS = {"index.html", "404.html"}


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        data = {key.lower(): (value or "") for key, value in attrs}
        href = data.get("href", "").strip()
        if href:
            self.hrefs.append(href)


def page_url_path(relative_html: str) -> str:
    """Convert a generated HTML path into its canonical site URL path."""
    relative_html = relative_html.replace("\\", "/")
    if relative_html == "index.html":
        return BASE_PATH
    if relative_html.endswith("/index.html"):
        return BASE_PATH + relative_html[: -len("index.html")]
    return BASE_PATH + relative_html


def normalize_internal_target(source_relative_html: str, href: str) -> str | None:
    """Resolve an internal href to a generated HTML path relative to site root."""
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:", "blob:")):
        return None

    parsed = urlparse(href)
    if parsed.scheme and parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc and parsed.netloc != BASE_HOST:
        return None

    source_url = "https://" + BASE_HOST + page_url_path(source_relative_html)
    resolved = urlparse(urljoin(source_url, href))
    if resolved.netloc != BASE_HOST or not resolved.path.startswith(BASE_PATH):
        return None

    path = unquote(resolved.path[len(BASE_PATH) :])
    path = posixpath.normpath("/" + path).lstrip("/")
    if path in {"", "."}:
        return "index.html"
    if resolved.path.endswith("/"):
        return path.rstrip("/") + "/index.html"
    if Path(path).suffix:
        return path
    return path.rstrip("/") + "/index.html"


def is_verification_file(path: Path, site: Path) -> bool:
    """Return True for root-level search/social ownership verification files."""
    if path.parent != site:
        return False
    text = path.read_text(encoding="utf-8", errors="strict").strip()
    return bool(VERIFICATION_PATTERN.match(text))


def audit(site: Path) -> dict[str, object]:
    site = site.resolve()
    html_files = sorted(site.rglob("*.html"))
    all_pages = {path.relative_to(site).as_posix() for path in html_files}
    verification_pages = {
        path.relative_to(site).as_posix()
        for path in html_files
        if is_verification_file(path, site)
    }
    navigable_pages = all_pages - verification_pages
    orphan_eligible_pages = navigable_pages - EXCLUDED_ORPHAN_PATHS

    inbound: Counter[str] = Counter()
    broken_targets: Counter[str] = Counter()

    for path in html_files:
        source = path.relative_to(site).as_posix()
        if source in verification_pages:
            continue
        parser = LinkParser()
        parser.feed(path.read_text(encoding="utf-8", errors="strict"))
        seen_from_source: set[str] = set()
        for href in parser.hrefs:
            target = normalize_internal_target(source, href)
            if target is None or target in seen_from_source:
                continue
            seen_from_source.add(target)
            if target in all_pages:
                inbound[target] += 1
            else:
                broken_targets[target] += 1

    orphan_pages = sorted(page for page in orphan_eligible_pages if inbound[page] == 0)
    page_records = [
        {
            "path": page,
            "inbound_internal_links": inbound[page],
            "orphan_eligible": page in orphan_eligible_pages,
        }
        for page in sorted(navigable_pages)
    ]
    return {
        "version": "33-orphan-pages",
        "pages_scanned": len(all_pages),
        "navigable_pages": len(navigable_pages),
        "verification_pages_skipped": sorted(verification_pages),
        "orphan_eligible_pages": len(orphan_eligible_pages),
        "orphan_page_count": len(orphan_pages),
        "orphan_pages": orphan_pages,
        "pages": page_records,
        "unresolved_internal_target_count": sum(broken_targets.values()),
        "unresolved_internal_targets": [
            {"path": path, "references": count}
            for path, count in sorted(broken_targets.items())
        ][:500],
    }


def main() -> int:
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
    if not site.is_dir():
        raise SystemExit(f"Site directory does not exist: {site}")
    report = audit(site)
    output = site / "api" / "orphan-pages-v33.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
