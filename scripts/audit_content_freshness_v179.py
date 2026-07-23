#!/usr/bin/env python3
"""Audit review freshness and source recency across content JSON and built HTML.

The audit is read-only. It never changes publication state, deletes pages, or
claims specialist review. It emits JSON and CSV evidence for editorial queues.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CONTENT_KEYS = {"title", "title_ar", "ar", "name", "heading"}
TEXT_KEYS = {"description", "summary", "content", "body", "sections", "paragraphs"}
RISK_LEVELS = {"low", "moderate", "high", "critical"}
PUBLISH_STATES = {"published", "reviewed"}
REVIEW_COMPLETE = {"internally-reviewed", "externally-reviewed", "reviewed"}


@dataclass
class Finding:
    source_file: str
    record_id: str
    title: str
    record_type: str
    risk_level: str
    status: str
    review_status: str
    reviewed_at: str
    age_days: int | None
    decision: str
    codes: list[str]
    source_count: int
    stale_source_count: int


class MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.json_ld: list[dict[str, Any]] = []
        self._in_json_ld = False
        self._json_buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "title":
            self._in_title = True
        elif tag.lower() == "meta":
            key = values.get("name") or values.get("property")
            if key:
                self.meta[key.lower()] = values.get("content", "")
        elif tag.lower() == "link" and values.get("rel", "").lower() == "canonical":
            self.canonical = values.get("href", "")
        elif tag.lower() == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
        elif tag.lower() == "script" and self._in_json_ld:
            self._in_json_ld = False
            raw = "".join(self._json_buffer).strip()
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    self.json_ld.append(payload)
                elif isinstance(payload, list):
                    self.json_ld.extend(x for x in payload if isinstance(x, dict))
            except json.JSONDecodeError:
                pass

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._json_buffer.append(data)


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not DATE_RE.match(text):
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def iter_records(value: Any, trail: str = "root") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        keys = set(value)
        has_identity = bool(keys & CONTENT_KEYS)
        has_substance = bool(keys & TEXT_KEYS)
        has_governance = bool(keys & {"status", "review_status", "reviewed_at", "risk_level", "sources", "references", "citations"})
        if has_identity and (has_substance or has_governance):
            yield trail, value
        for key, child in value.items():
            yield from iter_records(child, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_records(child, f"{trail}[{index}]")


def normalize_sources(record: dict[str, Any]) -> list[dict[str, Any]]:
    raw = record.get("sources") or record.get("references") or record.get("citations") or []
    if isinstance(raw, dict):
        raw = list(raw.values())
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def inspect_record(path: Path, pointer: str, record: dict[str, Any], today: date, max_age: int, source_max_age: int) -> Finding:
    title = str(record.get("title_ar") or record.get("title") or record.get("ar") or record.get("name") or record.get("heading") or pointer).strip()
    record_id = str(record.get("id") or record.get("entity_id") or record.get("slug") or pointer)
    status = str(record.get("status") or "unknown").strip().lower()
    review_status = str(record.get("review_status") or "unknown").strip().lower()
    risk = str(record.get("risk_level") or record.get("safety_level") or "unknown").strip().lower()
    if risk not in RISK_LEVELS:
        risk = "unknown"
    reviewed_text = str(record.get("reviewed_at") or record.get("dateModified") or "").strip()
    reviewed_date = parse_date(reviewed_text)
    age_days = (today - reviewed_date).days if reviewed_date else None
    sources = normalize_sources(record)
    stale_sources = 0
    undated_sources = 0
    for source in sources:
        source_date = parse_date(source.get("verified_at") or source.get("reviewed_at") or source.get("accessed_at") or source.get("published_at"))
        if not source_date:
            undated_sources += 1
        elif (today - source_date).days > source_max_age:
            stale_sources += 1

    codes: list[str] = []
    is_public_candidate = status in PUBLISH_STATES
    high_risk = risk in {"high", "critical"}

    if is_public_candidate and not reviewed_date:
        codes.append("published_without_review_date")
    if reviewed_date and age_days is not None and age_days > max_age:
        codes.append("review_overdue")
    if high_risk and review_status not in REVIEW_COMPLETE:
        codes.append("high_risk_review_incomplete")
    if high_risk and not sources:
        codes.append("high_risk_without_structured_sources")
    if high_risk and undated_sources:
        codes.append("high_risk_sources_without_dates")
    if stale_sources:
        codes.append("stale_source_verification")
    if status == "published" and review_status in {"unknown", "unreviewed", "needs-review", "needs-specialist-review"}:
        codes.append("published_with_incomplete_review_state")

    critical = {
        "published_without_review_date",
        "high_risk_review_incomplete",
        "high_risk_without_structured_sources",
        "published_with_incomplete_review_state",
    }
    if critical.intersection(codes):
        decision = "fix-before-publish"
    elif codes:
        decision = "needs-update"
    else:
        decision = "current"

    return Finding(
        source_file=str(path),
        record_id=record_id,
        title=title,
        record_type=str(record.get("content_type") or record.get("type") or "json-record"),
        risk_level=risk,
        status=status,
        review_status=review_status,
        reviewed_at=reviewed_text,
        age_days=age_days,
        decision=decision,
        codes=sorted(set(codes)),
        source_count=len(sources),
        stale_source_count=stale_sources,
    )


def inspect_html(path: Path, today: date, max_age: int) -> Finding:
    parser = MetaParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    modified = parser.meta.get("article:modified_time", "")
    if not modified:
        for block in parser.json_ld:
            candidate = block.get("dateModified")
            if candidate:
                modified = str(candidate)[:10]
                break
    modified_date = parse_date(modified[:10])
    age_days = (today - modified_date).days if modified_date else None
    codes: list[str] = []
    if not parser.title.strip():
        codes.append("html_missing_title")
    if not parser.meta.get("description", "").strip():
        codes.append("html_missing_meta_description")
    if not parser.canonical:
        codes.append("html_missing_canonical")
    if not modified_date:
        codes.append("html_missing_date_modified")
    elif age_days is not None and age_days > max_age:
        codes.append("html_review_overdue")
    decision = "fix-before-publish" if any(code.startswith("html_missing_") for code in codes) else ("needs-update" if codes else "current")
    return Finding(
        source_file=str(path),
        record_id=str(path),
        title=parser.title.strip() or path.stem,
        record_type="html-page",
        risk_level="unknown",
        status="built",
        review_status="unknown",
        reviewed_at=modified[:10],
        age_days=age_days,
        decision=decision,
        codes=sorted(codes),
        source_count=0,
        stale_source_count=0,
    )


def audit(root: Path, today: date, max_age: int = 365, source_max_age: int = 730) -> list[Finding]:
    findings: list[Finding] = []
    for base_name in ("content", "data"):
        base = root / base_name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for pointer, record in iter_records(payload):
                findings.append(inspect_record(path.relative_to(root), pointer, record, today, max_age, source_max_age))
    site = root / "_site"
    if site.exists():
        for path in sorted(site.rglob("*.html")):
            findings.append(inspect_html(path.relative_to(root), today, max_age))
    return findings


def write_reports(findings: list[Finding], output_json: Path, output_csv: Path, today: date, max_age: int, source_max_age: int) -> None:
    counts: dict[str, int] = {"current": 0, "needs-update": 0, "fix-before-publish": 0}
    for item in findings:
        counts[item.decision] = counts.get(item.decision, 0) + 1
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps({
        "schema_version": "1.0.0",
        "audit_id": "content-freshness-v179",
        "generated_at": today.isoformat(),
        "policy": {"content_review_max_age_days": max_age, "source_verification_max_age_days": source_max_age},
        "summary": {"records": len(findings), **counts},
        "findings": [asdict(item) for item in findings],
        "publication_rule": "This report is advisory evidence. It never proves specialist review or live publication and never changes publication state automatically.",
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_file", "record_id", "title", "record_type", "risk_level", "status", "review_status", "reviewed_at", "age_days", "decision", "codes", "source_count", "stale_source_count"])
        writer.writeheader()
        for item in findings:
            row = asdict(item)
            row["codes"] = "|".join(item.codes)
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--output-json", default="artifacts/content-freshness-v179.json")
    parser.add_argument("--output-csv", default="artifacts/content-freshness-v179.csv")
    parser.add_argument("--today", default=date.today().isoformat())
    parser.add_argument("--max-age-days", type=int, default=365)
    parser.add_argument("--source-max-age-days", type=int, default=730)
    args = parser.parse_args()
    today = parse_date(args.today)
    if not today:
        raise SystemExit("--today must use YYYY-MM-DD")
    findings = audit(Path(args.root), today, args.max_age_days, args.source_max_age_days)
    write_reports(findings, Path(args.output_json), Path(args.output_csv), today, args.max_age_days, args.source_max_age_days)
    blockers = sum(item.decision == "fix-before-publish" for item in findings)
    print(json.dumps({"records": len(findings), "fix_before_publish": blockers}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
