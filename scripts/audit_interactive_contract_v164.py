import argparse
import csv
import json
import re
from html.parser import HTMLParser
from pathlib import Path


INTERACTIVE_MARKERS = re.compile(
    r"<(?:form|input|select|textarea)\b|data-(?:assessment|cognitive|sleep-log|daily-tool)",
    re.I,
)
BOUNDARY_RE = re.compile(r"غير\s+تشخيص|لا\s+يشخ[ّص]|not\s+diagnostic", re.I)
HELP_RE = re.compile(r"مختص|مساعدة\s+مهنية|طلب\s+المساعدة|professional\s+help|healthcare\s+professional", re.I)
PRIVACY_RE = re.compile(r"خصوصي|محلي|local\s+storage|stored\s+locally", re.I)
DELETE_RE = re.compile(r"حذف|مسح|delete|clear", re.I)
EXPORT_RE = re.compile(r"تصدير|تنزيل|export|download|print|طباعة", re.I)
NETWORK_RE = re.compile(r"\b(?:fetch|XMLHttpRequest|sendBeacon|WebSocket)\s*\(", re.I)


class AuditParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.html_attrs = {}
        self.h1_count = 0
        self.labels_for = set()
        self.control_ids = []
        self.unlabelled_controls = []
        self.button_stack = []
        self.unnamed_buttons = []
        self.images_without_alt = 0

    @staticmethod
    def attrs_dict(attrs):
        return {str(k).lower(): ("" if v is None else str(v)) for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        data = self.attrs_dict(attrs)
        if tag == "html":
            self.html_attrs = data
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "label" and data.get("for"):
            self.labels_for.add(data["for"])
        elif tag in {"input", "select", "textarea"}:
            if tag == "input" and data.get("type", "").lower() in {"hidden", "submit", "button", "reset", "image"}:
                return
            control_id = data.get("id", "")
            has_name = bool(data.get("aria-label") or data.get("aria-labelledby") or data.get("title"))
            self.control_ids.append((control_id, has_name))
        elif tag == "button":
            has_name = bool(data.get("aria-label") or data.get("aria-labelledby") or data.get("title"))
            self.button_stack.append({"named": has_name, "text": []})
        elif tag == "img" and "alt" not in data:
            self.images_without_alt += 1

    def handle_data(self, data):
        if self.button_stack:
            self.button_stack[-1]["text"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "button" and self.button_stack:
            button = self.button_stack.pop()
            if not button["named"] and not "".join(button["text"]).strip():
                self.unnamed_buttons.append(True)

    def finalize(self):
        for control_id, has_name in self.control_ids:
            if has_name:
                continue
            if not control_id or control_id not in self.labels_for:
                self.unlabelled_controls.append(control_id or "(missing-id)")


def audit_file(path: Path, root: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if not INTERACTIVE_MARKERS.search(text):
        return None

    parser = AuditParser()
    parser.feed(text)
    parser.finalize()
    lower = text.lower()
    critical = []
    warnings = []

    lang = parser.html_attrs.get("lang", "").lower()
    direction = parser.html_attrs.get("dir", "").lower()
    if not lang:
        critical.append("missing_html_lang")
    if lang.startswith("ar") and direction != "rtl":
        critical.append("arabic_page_not_rtl")
    if parser.h1_count != 1:
        critical.append("h1_count_not_one")
    if parser.unlabelled_controls:
        critical.append("unlabelled_form_controls")
    if parser.unnamed_buttons:
        critical.append("unnamed_buttons")
    if not BOUNDARY_RE.search(text):
        critical.append("missing_non_diagnostic_boundary")
    if not HELP_RE.search(text):
        warnings.append("missing_help_seeking_guidance")
    if parser.images_without_alt:
        warnings.append("images_without_alt")

    uses_local_storage = "localstorage" in lower or "indexeddb" in lower
    if uses_local_storage and not PRIVACY_RE.search(text):
        critical.append("local_storage_without_privacy_notice")
    if uses_local_storage and not DELETE_RE.search(text):
        warnings.append("local_storage_without_visible_delete_language")
    if uses_local_storage and not EXPORT_RE.search(text):
        warnings.append("local_storage_without_export_or_print_language")
    if NETWORK_RE.search(text):
        critical.append("network_transmission_api_detected")

    return {
        "path": path.relative_to(root).as_posix(),
        "lang": lang,
        "dir": direction,
        "h1_count": parser.h1_count,
        "form_controls": len(parser.control_ids),
        "unlabelled_controls": parser.unlabelled_controls,
        "unnamed_buttons": len(parser.unnamed_buttons),
        "images_without_alt": parser.images_without_alt,
        "uses_local_storage": uses_local_storage,
        "critical": sorted(set(critical)),
        "warnings": sorted(set(warnings)),
    }


def run(site: Path):
    pages = []
    for path in sorted(site.rglob("*.html")):
        result = audit_file(path, site)
        if result:
            pages.append(result)
    return {
        "schema_version": "1.0.0",
        "site": str(site),
        "interactive_pages": len(pages),
        "pages_with_critical_findings": sum(bool(page["critical"]) for page in pages),
        "pages_with_warnings": sum(bool(page["warnings"]) for page in pages),
        "critical_findings": sum(len(page["critical"]) for page in pages),
        "warning_findings": sum(len(page["warnings"]) for page in pages),
        "pages": pages,
    }


def write_csv(report, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["path", "lang", "dir", "h1_count", "form_controls", "critical", "warnings"],
        )
        writer.writeheader()
        for page in report["pages"]:
            writer.writerow({
                "path": page["path"],
                "lang": page["lang"],
                "dir": page["dir"],
                "h1_count": page["h1_count"],
                "form_controls": page["form_controls"],
                "critical": "|".join(page["critical"]),
                "warnings": "|".join(page["warnings"]),
            })


def main():
    parser = argparse.ArgumentParser(description="Audit interactive psychology tools without making clinical-validity claims.")
    parser.add_argument("site", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--csv", dest="csv_path", type=Path)
    parser.add_argument("--fail-on-critical", action="store_true")
    args = parser.parse_args()

    if not args.site.is_dir():
        parser.error(f"site directory does not exist: {args.site}")

    report = run(args.site)
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.csv_path:
        write_csv(report, args.csv_path)

    print(json.dumps({
        "interactive_pages": report["interactive_pages"],
        "pages_with_critical_findings": report["pages_with_critical_findings"],
        "critical_findings": report["critical_findings"],
        "warning_findings": report["warning_findings"],
    }, ensure_ascii=False))

    if args.fail_on_critical and report["critical_findings"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
