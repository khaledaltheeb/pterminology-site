from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_SITE = Path("_site")
REPORT_PATH = Path("api/public-shell-language-v208.json")

# Person-label forms are prohibited in public output. The scientific/legal noun
# «الإعاقة» remains available where it is necessary and accurately contextualised.
PROHIBITED_PERSON_LABEL = re.compile(
    r"(?<![\u0600-\u06FF])(?:ال)?معاق(?:ة|ون|ين)?(?![\u0600-\u06FF])"
)
VERIFICATION_CONTENT = re.compile(
    r"^(?:google-site-verification|msvalidate\.01|p:domain_verify|facebook-domain-verification)\s*[:=]",
    re.IGNORECASE,
)
HEADER = re.compile(r"<header\b", re.IGNORECASE)
FOOTER = re.compile(r"<footer\b", re.IGNORECASE)
TAG = re.compile(r"<[^>]+>")
WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str
    evidence: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "kind": self.kind, "evidence": self.evidence}


def is_verification_artifact(site: Path, page: Path, html: str) -> bool:
    return page.parent == site and bool(VERIFICATION_CONTENT.match(html.strip()))


def evidence_window(text: str, match: re.Match[str], radius: int = 75) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    fragment = TAG.sub(" ", text[start:end])
    return WHITESPACE.sub(" ", fragment).strip()


def iter_public_pages(site: Path) -> Iterable[tuple[Path, str]]:
    for page in sorted(site.rglob("*.html")):
        html = page.read_text(encoding="utf-8", errors="replace")
        if is_verification_artifact(site, page, html):
            continue
        yield page, html


def audit_site(site: Path) -> dict[str, object]:
    site = site.resolve()
    if not site.is_dir():
        raise FileNotFoundError(f"Site directory does not exist: {site}")

    findings: list[Finding] = []
    pages_scanned = 0
    pages_with_prohibited_language: set[str] = set()
    missing_header: list[str] = []
    missing_footer: list[str] = []

    for page, html in iter_public_pages(site):
        pages_scanned += 1
        relative = page.relative_to(site).as_posix()

        if not HEADER.search(html):
            missing_header.append(relative)
            findings.append(Finding(relative, "missing-header", "No semantic <header> element"))
        if not FOOTER.search(html):
            missing_footer.append(relative)
            findings.append(Finding(relative, "missing-footer", "No semantic <footer> element"))

        for match in PROHIBITED_PERSON_LABEL.finditer(html):
            pages_with_prohibited_language.add(relative)
            findings.append(
                Finding(
                    relative,
                    "prohibited-person-label",
                    evidence_window(html, match),
                )
            )

    report: dict[str, object] = {
        "version": 208,
        "status": "pass" if not findings else "fail",
        "site": str(site),
        "pages_scanned": pages_scanned,
        "prohibited_person_label_pages": len(pages_with_prohibited_language),
        "prohibited_person_label_occurrences": sum(
            finding.kind == "prohibited-person-label" for finding in findings
        ),
        "missing_header_pages": len(missing_header),
        "missing_footer_pages": len(missing_footer),
        "excluded_verification_artifacts": sum(
            1
            for page in site.glob("*.html")
            if is_verification_artifact(
                site,
                page,
                page.read_text(encoding="utf-8", errors="replace"),
            )
        ),
        "policy": {
            "preferred_platform_term": "ذوو الاحتياجات الخاصة",
            "contextual_scientific_term_allowed": "الإعاقة",
            "requires_semantic_header": True,
            "requires_semantic_footer": True,
        },
        "missing_header": missing_header,
        "missing_footer": missing_footer,
        "findings": [finding.as_dict() for finding in findings[:500]],
        "findings_truncated": max(0, len(findings) - 500),
    }
    return report


def write_report(site: Path, report: dict[str, object]) -> Path:
    output = site / REPORT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit public Arabic language and semantic header/footer coverage."
    )
    parser.add_argument("site", nargs="?", type=Path, default=DEFAULT_SITE)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Write the report without returning a failing process status.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = audit_site(args.site)
    output = write_report(args.site.resolve(), report)
    print(json.dumps({**report, "report": str(output)}, ensure_ascii=False, indent=2))
    if report["status"] != "pass" and not args.report_only:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
