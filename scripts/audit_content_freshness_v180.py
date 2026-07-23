#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, json, re
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
    def handle_starttag(self, tag, attrs):
        values = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()
        if tag == "title": self._in_title = True
        elif tag == "meta":
            key = values.get("name") or values.get("property")
            if key: self.meta[key.lower()] = values.get("content", "")
        elif tag == "link" and values.get("rel", "").lower() == "canonical":
            self.canonical = values.get("href", "")
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True; self._json_buffer = []
    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title": self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            try:
                payload = json.loads("".join(self._json_buffer).strip())
                if isinstance(payload, dict): self.json_ld.append(payload)
                elif isinstance(payload, list): self.json_ld.extend(x for x in payload if isinstance(x, dict))
            except json.JSONDecodeError: pass
    def handle_data(self, data):
        if self._in_title: self.title += data
        if self._in_json_ld: self._json_buffer.append(data)

def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not DATE_RE.match(text): return None
    try: return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError: return None

def iter_records(value: Any, trail="root") -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(value, dict):
        keys = set(value)
        if keys & CONTENT_KEYS and (keys & TEXT_KEYS or keys & {"status","review_status","reviewed_at","risk_level","sources","references","citations"}):
            yield trail, value
        for key, child in value.items(): yield from iter_records(child, f"{trail}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value): yield from iter_records(child, f"{trail}[{index}]")

def normalize_sources(record):
    raw = record.get("sources") or record.get("references") or record.get("citations") or []
    if isinstance(raw, dict): raw = list(raw.values())
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []

def inspect_record(path, pointer, record, today, max_age, source_max_age):
    title = str(record.get("title_ar") or record.get("title") or record.get("ar") or record.get("name") or record.get("heading") or pointer).strip()
    record_id = str(record.get("id") or record.get("entity_id") or record.get("slug") or pointer)
    status = str(record.get("status") or "unknown").strip().lower()
    review_status = str(record.get("review_status") or "unknown").strip().lower()
    risk = str(record.get("risk_level") or record.get("safety_level") or "unknown").strip().lower()
    if risk not in RISK_LEVELS: risk = "unknown"
    reviewed_text = str(record.get("reviewed_at") or record.get("dateModified") or "").strip()
    reviewed_date = parse_date(reviewed_text)
    age_days = (today - reviewed_date).days if reviewed_date else None
    sources = normalize_sources(record)
    stale_sources = undated_sources = 0
    for source in sources:
        source_date = parse_date(source.get("verified_at") or source.get("reviewed_at") or source.get("accessed_at") or source.get("published_at"))
        if not source_date: undated_sources += 1
        elif (today - source_date).days > source_max_age: stale_sources += 1
    codes = []
    high_risk = risk in {"high", "critical"}
    if status in PUBLISH_STATES and not reviewed_date: codes.append("published_without_review_date")
    if reviewed_date and age_days is not None and age_days > max_age: codes.append("review_overdue")
    if high_risk and review_status not in REVIEW_COMPLETE: codes.append("high_risk_review_incomplete")
    if high_risk and not sources: codes.append("high_risk_without_structured_sources")
    if high_risk and undated_sources: codes.append("high_risk_sources_without_dates")
    if stale_sources: codes.append("stale_source_verification")
    if status == "published" and review_status in {"unknown","unreviewed","needs-review","needs-specialist-review"}: codes.append("published_with_incomplete_review_state")
    critical = {"published_without_review_date","high_risk_review_incomplete","high_risk_without_structured_sources","published_with_incomplete_review_state"}
    decision = "fix-before-publish" if critical.intersection(codes) else ("needs-update" if codes else "current")
    return Finding(str(path), record_id, title, str(record.get("content_type") or record.get("type") or "json-record"), risk, status, review_status, reviewed_text, age_days, decision, sorted(set(codes)), len(sources), stale_sources)

def inspect_html(actual_path: Path, display_path: Path, today: date, max_age: int) -> Finding:
    parser = MetaParser(); parser.feed(actual_path.read_text(encoding="utf-8", errors="replace"))
    modified = parser.meta.get("article:modified_time", "")
    if not modified:
        for block in parser.json_ld:
            if block.get("dateModified"):
                modified = str(block["dateModified"])[:10]; break
    modified_date = parse_date(modified[:10]); age_days = (today - modified_date).days if modified_date else None
    codes = []
    if not parser.title.strip(): codes.append("html_missing_title")
    if not parser.meta.get("description", "").strip(): codes.append("html_missing_meta_description")
    if not parser.canonical: codes.append("html_missing_canonical")
    if not modified_date: codes.append("html_missing_date_modified")
    elif age_days is not None and age_days > max_age: codes.append("html_review_overdue")
    decision = "fix-before-publish" if any(c.startswith("html_missing_") for c in codes) else ("needs-update" if codes else "current")
    return Finding(str(display_path), str(display_path), parser.title.strip() or actual_path.stem, "html-page", "unknown", "built", "unknown", modified[:10], age_days, decision, sorted(codes), 0, 0)

def audit(root: Path, today: date, max_age=365, source_max_age=730):
    findings = []
    for base_name in ("content", "data"):
        base = root / base_name
        if not base.exists(): continue
        for path in sorted(base.rglob("*.json")):
            try: payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError): continue
            for pointer, record in iter_records(payload): findings.append(inspect_record(path.relative_to(root), pointer, record, today, max_age, source_max_age))
    site = root / "_site"
    if site.exists():
        for path in sorted(site.rglob("*.html")): findings.append(inspect_html(path, path.relative_to(root), today, max_age))
    return findings

def write_reports(findings, output_json, output_csv, today, max_age, source_max_age):
    counts = {"current":0,"needs-update":0,"fix-before-publish":0}
    for item in findings: counts[item.decision] = counts.get(item.decision, 0) + 1
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps({"schema_version":"1.0.0","audit_id":"content-freshness-v180","generated_at":today.isoformat(),"policy":{"content_review_max_age_days":max_age,"source_verification_max_age_days":source_max_age},"summary":{"records":len(findings),**counts},"findings":[asdict(x) for x in findings],"publication_rule":"This report is advisory evidence. It never proves specialist review or live publication and never changes publication state automatically."}, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    with output_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        fields=["source_file","record_id","title","record_type","risk_level","status","review_status","reviewed_at","age_days","decision","codes","source_count","stale_source_count"]
        writer=csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for item in findings:
            row=asdict(item); row["codes"]="|".join(item.codes); writer.writerow(row)

def main():
    p=argparse.ArgumentParser(); p.add_argument("root", nargs="?", default="."); p.add_argument("--output-json", default="artifacts/content-freshness-v180.json"); p.add_argument("--output-csv", default="artifacts/content-freshness-v180.csv"); p.add_argument("--today", default=date.today().isoformat()); p.add_argument("--max-age-days", type=int, default=365); p.add_argument("--source-max-age-days", type=int, default=730)
    a=p.parse_args(); today=parse_date(a.today)
    if not today: raise SystemExit("--today must use YYYY-MM-DD")
    findings=audit(Path(a.root), today, a.max_age_days, a.source_max_age_days); write_reports(findings, Path(a.output_json), Path(a.output_csv), today, a.max_age_days, a.source_max_age_days)
    print(json.dumps({"records":len(findings),"fix_before_publish":sum(x.decision=="fix-before-publish" for x in findings)}, ensure_ascii=False)); return 0
if __name__ == "__main__": raise SystemExit(main())
