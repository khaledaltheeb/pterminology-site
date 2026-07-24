#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

LABEL_OLD = '<label class="field"><span>البحث داخل المركز</span>'
LABEL_NEW = '<label class="field" for="hub-search"><span>البحث داخل المركز</span>'
INPUT_OLD = '<input id="hub-search" type="search" placeholder='
INPUT_NEW = '<input id="hub-search" type="search" aria-label="البحث داخل مركز ذوي الاحتياجات الخاصة" placeholder='


def finalize(site: Path) -> dict[str, object]:
    page = site / "special-needs" / "index.html"
    if not page.is_file():
        raise SystemExit(f"Missing generated special-needs hub: {page}")

    text = page.read_text(encoding="utf-8")
    if text.count('id="hub-search"') != 1:
        raise SystemExit("Expected exactly one special-needs hub search input")

    label_changed = False
    input_changed = False
    if 'for="hub-search"' not in text:
        if LABEL_OLD not in text:
            raise SystemExit("Special-needs search label marker changed; refusing unsafe accessibility patch")
        text = text.replace(LABEL_OLD, LABEL_NEW, 1)
        label_changed = True

    if 'aria-label="البحث داخل مركز ذوي الاحتياجات الخاصة"' not in text:
        if INPUT_OLD not in text:
            raise SystemExit("Special-needs search input marker changed; refusing unsafe accessibility patch")
        text = text.replace(INPUT_OLD, INPUT_NEW, 1)
        input_changed = True

    if text.count('for="hub-search"') != 1:
        raise SystemExit("Search input must have exactly one explicit label association")
    if text.count('aria-label="البحث داخل مركز ذوي الاحتياجات الخاصة"') != 1:
        raise SystemExit("Search input must have exactly one accessible name")

    page.write_text(text, encoding="utf-8")

    report_path = site / "api" / "special-needs-hub-v201.json"
    if report_path.is_file():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report = {"version": 201, "output": "special-needs/index.html"}
    report["search_accessibility"] = {
        "explicit_label_for": True,
        "accessible_name": True,
        "input_id": "hub-search",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    guides_publisher = Path(__file__).with_name("publish_special_needs_guides_v209_compat.py")
    subprocess.run([sys.executable, str(guides_publisher), str(site)], check=True)
    guides_report_path = site / "api" / "special-needs-guides-v209.json"
    if not guides_report_path.is_file():
        raise SystemExit("v209 publisher completed without an evidence report")
    guides_report = json.loads(guides_report_path.read_text(encoding="utf-8"))
    if guides_report.get("guide_count") != 5 or not guides_report.get("hub_linked"):
        raise SystemExit(f"Invalid v209 guide report: {guides_report}")

    result = {
        "version": 201,
        "page": "special-needs/index.html",
        "label_changed": label_changed,
        "input_changed": input_changed,
        "explicit_label_for": True,
        "accessible_name": True,
        "special_needs_guides_version": 209,
        "special_needs_guides": guides_report["guide_count"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
    if not target.is_dir():
        raise SystemExit(f"Missing site directory: {target}")
    finalize(target)
