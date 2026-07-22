from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
HOME = SITE / "index.html"


def main() -> None:
    if not HOME.exists():
        raise SystemExit("Missing generated homepage")
    text = HOME.read_text(encoding="utf-8")
    nav_anchor = '<a href="hubs/">المراكز</a>'
    blog_anchor = '<a href="blog/">المدونة</a>'
    if blog_anchor not in text:
        if nav_anchor not in text:
            raise SystemExit("Homepage navigation anchor changed")
        text = text.replace(nav_anchor, blog_anchor + nav_anchor, 1)

    card_anchor = '<article class="card"><h3>المراكز الموضوعية</h3>'
    blog_card = '<article class="card"><h3>المدونة التحليلية</h3><p>مقالات ركيزية تشرح الفروق النفسية والأسئلة اليومية بمصادر موثقة وروابط إلى الموسوعة والأدوات.</p><a href="blog/">قراءة مقالات المدونة</a></article>'
    if blog_card not in text:
        if card_anchor not in text:
            raise SystemExit("Homepage cards anchor changed")
        text = text.replace(card_anchor, blog_card + card_anchor, 1)

    HOME.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
