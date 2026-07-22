from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "daily-tools" / "sleep-wind-down-plan" / "index.html"

BUTTON = '<button type="button" data-export-svg aria-describedby="sleep-svg-export-privacy">تصدير المخطط SVG</button>'
DISCLOSURE = (
    '<p id="sleep-svg-export-privacy" class="privacy">'
    'ملف SVG يتضمن تواريخ النوم ومدته ودرجات الجودة والطاقة، ولا يتضمن الملاحظات النصية. '
    'راجع الملف قبل مشاركته. المشاركة اختيارية وتتم خارج التخزين المحلي لهذا الجهاز.'
    '</p>'
)


def patch() -> None:
    if not PAGE.is_file():
        raise SystemExit(f"Missing generated sleep page: {PAGE}")

    text = PAGE.read_text(encoding="utf-8")

    if 'data-export-svg' not in text:
        anchor = '<button type="button" data-print-sleep>طباعة</button>'
        if anchor not in text:
            raise SystemExit("Sleep export actions anchor was not found")
        text = text.replace(anchor, f'{BUTTON}{anchor}', 1)

    if 'id="sleep-svg-export-privacy"' not in text:
        chart_heading = '<h2>مخطط الاتجاهات لآخر 14 سجلًا</h2>'
        if chart_heading not in text:
            raise SystemExit("Sleep chart heading was not found")
        text = text.replace(chart_heading, f'{chart_heading}{DISCLOSURE}', 1)

    PAGE.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch()
