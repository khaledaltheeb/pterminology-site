from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "daily-tools" / "weekly-function-review" / "index.html"
ASSET = SITE / "assets" / "weekly-function-review-v36.js"
REPORT = SITE / "api" / "weekly-function-review-v36.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    require(PAGE.exists(), f"missing page: {PAGE}")
    require(ASSET.exists(), f"missing asset: {ASSET}")
    require(REPORT.exists(), f"missing report: {REPORT}")
    html = PAGE.read_text(encoding="utf-8")
    js = ASSET.read_text(encoding="utf-8")
    report = json.loads(REPORT.read_text(encoding="utf-8"))

    for field in ("sleep", "energy", "focus", "relationships", "tasks"):
        require(f'name="{field}"' in html, f"missing question {field}")
        require(re.search(rf'id="{field}"[^>]+min="0"[^>]+max="10"', html), f"invalid bounds {field}")

    required_html = [
        'data-weekly-review-v36',
        'weekly-review-storage-consent',
        'weekly-review-history-body',
        'weekly-review-chart-text',
        'weekly-review-export-json',
        'weekly-review-export-csv',
        'weekly-review-print',
        'weekly-review-clear',
        'aria-live="polite"',
        'prefers-reduced-motion',
        '@media print',
        'لا تُرسل البيانات إلى خادم',
        'غير تشخيصية',
        'خدمات الطوارئ المحلية',
    ]
    for marker in required_html:
        require(marker in html, f"missing html contract: {marker}")

    required_js = [
        'validateEntry',
        'calculateSummary',
        'saveEntry',
        'clearHistory',
        'exportJson',
        'exportCsv',
        'localStorage',
        'window.print()',
        'history.slice(-52)',
    ]
    for marker in required_js:
        require(marker in js, f"missing js contract: {marker}")

    forbidden = [r'fetch\s*\(', r'XMLHttpRequest', r'navigator\.sendBeacon', r'تشخيصك', r'بديل عن الطبيب', r'يعالج نهائيًا']
    joined = html + "\n" + js
    for pattern in forbidden:
        require(not re.search(pattern, joined, flags=re.I), f"forbidden pattern: {pattern}")

    require(report["questions"] == 5, report)
    require(report["rating_min"] == 0 and report["rating_max"] == 10, report)
    require(report["storage"] == "optional-local-only", report)
    require(report["history_limit"] == 52, report)
    require(report["exports"] == ["json", "csv", "print"], report)
    require(report["delete_all"] is True and report["non_diagnostic"] is True, report)
    print(json.dumps({"weekly_function_review_v36": "passed", **report}, ensure_ascii=False))


if __name__ == "__main__":
    main()
