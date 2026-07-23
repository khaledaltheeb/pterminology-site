from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

HOST = "khaledaltheeb.github.io"
BASE_PATH = "/pterminology-site/"
BASE_URL = f"https://{HOST}{BASE_PATH.rstrip('/')}"
VERSION = 198
TEXT_SUFFIXES = {
    ".html",
    ".htm",
    ".xml",
    ".json",
    ".webmanifest",
    ".js",
    ".mjs",
    ".css",
    ".svg",
    ".txt",
}

ABSOLUTE_INTERNAL_RE = re.compile(
    r"(?P<prefix>(?:https?:)?//)"
    + re.escape(HOST)
    + r"(?P<path>/[^\s\"'<>)]*)?",
    re.IGNORECASE,
)
QUOTED_ROOT_RE = re.compile(
    r"(?P<quote>[\"'])(?P<path>/(?!/|pterminology-site(?:/|$)|[?#])[^\"']*)"
)
UNQUOTED_ATTRIBUTE_RE = re.compile(
    r"(?P<prefix>\b(?:href|src|action|poster|data)\s*=\s*)"
    r"(?P<path>/(?!/|pterminology-site(?:/|\b)|[?#])[^\s>]+)",
    re.IGNORECASE,
)
CSS_URL_RE = re.compile(
    r"(?P<prefix>url\(\s*)(?P<path>/(?!/|pterminology-site(?:/|\b)|[?#])[^\s)]+)(?P<suffix>\s*\))",
    re.IGNORECASE,
)


def normalize_absolute(match: re.Match[str]) -> str:
    path = match.group("path") or "/"
    if path == "/":
        return BASE_URL + "/"
    if path == BASE_PATH.rstrip("/"):
        return BASE_URL
    if path.startswith(BASE_PATH):
        return "https://" + HOST + path
    return BASE_URL + path


def normalize_text(text: str) -> tuple[str, int]:
    replacements = 0

    def replace_absolute(match: re.Match[str]) -> str:
        nonlocal replacements
        original = match.group(0)
        fixed = normalize_absolute(match)
        if fixed != original:
            replacements += 1
        return fixed

    text = ABSOLUTE_INTERNAL_RE.sub(replace_absolute, text)

    def replace_quoted(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return f'{match.group("quote")}{BASE_PATH}{match.group("path").lstrip("/")}'

    text = QUOTED_ROOT_RE.sub(replace_quoted, text)

    def replace_unquoted(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return f'{match.group("prefix")}{BASE_PATH}{match.group("path").lstrip("/")}'

    text = UNQUOTED_ATTRIBUTE_RE.sub(replace_unquoted, text)

    def replace_css(match: re.Match[str]) -> str:
        nonlocal replacements
        replacements += 1
        return (
            f'{match.group("prefix")}{BASE_PATH}'
            f'{match.group("path").lstrip("/")}{match.group("suffix")}'
        )

    text = CSS_URL_RE.sub(replace_css, text)
    return text, replacements


def text_files(site: Path) -> Iterable[Path]:
    for path in sorted(site.rglob("*")):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def bad_references(text: str) -> list[str]:
    errors: list[str] = []
    for match in ABSOLUTE_INTERNAL_RE.finditer(text):
        path = match.group("path") or "/"
        if path == "/" or not (
            path == BASE_PATH.rstrip("/") or path.startswith(BASE_PATH)
        ):
            errors.append(match.group(0))
    errors.extend(match.group(0) for match in QUOTED_ROOT_RE.finditer(text))
    errors.extend(match.group(0) for match in UNQUOTED_ATTRIBUTE_RE.finditer(text))
    errors.extend(match.group(0) for match in CSS_URL_RE.finditer(text))
    return errors


def normalize_site(site: Path, *, check_only: bool = False) -> dict[str, object]:
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")

    scanned = 0
    changed_files: list[str] = []
    replacements = 0
    decode_skipped: list[str] = []

    for path in text_files(site):
        scanned += 1
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            decode_skipped.append(path.relative_to(site).as_posix())
            continue
        normalized, count = normalize_text(original)
        replacements += count
        if normalized != original:
            changed_files.append(path.relative_to(site).as_posix())
            if not check_only:
                path.write_text(normalized, encoding="utf-8")

    remaining: list[dict[str, object]] = []
    for path in text_files(site):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        refs = bad_references(text)
        if refs:
            remaining.append(
                {
                    "file": path.relative_to(site).as_posix(),
                    "references": refs[:20],
                    "count": len(refs),
                }
            )

    report: dict[str, object] = {
        "version": VERSION,
        "status": "passed" if not remaining else "failed",
        "host": HOST,
        "required_base_path": BASE_PATH,
        "files_scanned": scanned,
        "files_changed": len(changed_files),
        "changed_files": changed_files,
        "replacements": replacements,
        "decode_skipped": decode_skipped,
        "remaining_error_files": len(remaining),
        "remaining_errors": remaining,
        "example_fixed": {
            "before": "https://khaledaltheeb.github.io/care-guides/",
            "after": "https://khaledaltheeb.github.io/pterminology-site/care-guides/",
        },
    }

    if not check_only:
        output = site / "api" / "internal-base-paths-v198.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", default="_site", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    report = normalize_site(args.site.resolve(), check_only=args.check_only)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["status"] != "passed":
        raise SystemExit("Internal GitHub Pages links without /pterminology-site/ remain")


if __name__ == "__main__":
    main()
