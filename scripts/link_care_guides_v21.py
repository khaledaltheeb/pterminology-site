from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "index.html"


def main() -> None:
    if not PAGE.exists():
        raise SystemExit("Production homepage is missing")
    text = PAGE.read_text(encoding="utf-8")
    if 'href="care-guides/"' not in text:
        nav_marker = '<a href="tips/">النصائح</a>'
        action_marker = '<a class="btn secondary" href="tips/">افتح الأدلة العملية</a>'
        if nav_marker not in text or action_marker not in text:
            raise SystemExit("Homepage markers changed; refusing unsafe care-guide injection")
        text = text.replace(nav_marker, nav_marker + '<a href="care-guides/">أدلة التعامل</a>', 1)
        text = text.replace(action_marker, action_marker + '<a class="btn secondary" href="care-guides/">أدلة التعامل مع الحالات</a>', 1)
    PAGE.write_text(text, encoding="utf-8")
    report = {
        "version": 21,
        "care_guides_linked": text.count('href="care-guides/"') >= 2,
        "navigation_link": '<a href="care-guides/">أدلة التعامل</a>' in text,
        "hero_link": 'أدلة التعامل مع الحالات' in text,
    }
    if not all(report[key] for key in ("care_guides_linked", "navigation_link", "hero_link")):
        raise SystemExit(f"Care-guide homepage integration failed: {report}")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-homepage-v21.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
