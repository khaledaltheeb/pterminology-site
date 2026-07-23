#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v182" / "privacy-mental-health-tools-ar.json"
CANONICAL = "https://khaledaltheeb.github.io/pterminology-site/care-guides/privacy-mental-health-tools/"


def load_content() -> dict:
    return json.loads(CONTENT.read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_page(data: dict) -> str:
    sections = "\n".join(
        f'<section><h2>{esc(section["heading"])}</h2>'
        + "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
        + "</section>"
        for section in data["sections"]
    )
    checklist = "".join(f"<li>{esc(item)}</li>" for item in data["checklist"])
    links = "".join(
        f'<li><a href="{esc(item["href"])}">{esc(item["label"])}</a></li>'
        for item in data["internal_links"]
    )
    sources = "".join(
        f'<li><a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(source["publisher"])} — {esc(source["title"])}</a> ({esc(source["year"])})</li>'
        for source in data["sources"]
    )
    citations = [source["url"] for source in data["sources"]]
    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": data["title"],
        "description": data["description"],
        "inLanguage": "ar",
        "dateModified": data["reviewed_at"],
        "mainEntityOfPage": CANONICAL,
        "citation": citations,
        "isPartOf": {
            "@type": "WebSite",
            "name": "مصطلحات علم النفس",
            "url": "https://khaledaltheeb.github.io/pterminology-site/",
        },
    }
    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": "https://khaledaltheeb.github.io/pterminology-site/"},
            {"@type": "ListItem", "position": 2, "name": "أدلة التعامل", "item": "https://khaledaltheeb.github.io/pterminology-site/care-guides/"},
            {"@type": "ListItem", "position": 3, "name": data["title"], "item": CANONICAL},
        ],
    }
    schemas = json.dumps([article_schema, breadcrumb_schema], ensure_ascii=False)
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data["title"])} | مصطلحات علم النفس</title>
<meta name="description" content="{esc(data["description"])}">
<link rel="canonical" href="{CANONICAL}">
<meta property="og:type" content="article">
<meta property="og:locale" content="ar_AR">
<meta property="og:title" content="{esc(data["title"])}">
<meta property="og:description" content="{esc(data["description"])}">
<meta property="og:url" content="{CANONICAL}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(data["title"])}">
<meta name="twitter:description" content="{esc(data["description"])}">
<script type="application/ld+json">{schemas}</script>
<style>
:root{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#172421;background:#f8f7f2;line-height:1.8}}
body{{margin:0}}main{{max-width:880px;margin:auto;padding:24px}}a{{color:#075f5a}}.skip{{position:absolute;right:-9999px}}.skip:focus{{right:12px;top:12px;background:#fff;padding:10px;z-index:5}}header,section,.panel{{background:#fff;border:1px solid #d9dfda;border-radius:18px;padding:22px;margin:0 0 18px}}h1{{font-size:clamp(2rem,6vw,3.4rem);line-height:1.25}}h2{{font-size:1.45rem;line-height:1.45}}.meta{{color:#4a5a55}}.warning{{border-inline-start:6px solid #8a5b00}}ul{{padding-inline-start:1.4rem}}@media print{{body{{background:#fff}}.skip{{display:none}}header,section,.panel{{border:0;break-inside:avoid}}}}
</style>
</head>
<body>
<a class="skip" href="#main">تجاوز إلى المحتوى</a>
<main id="main">
<header>
<p class="meta">دليل تثقيفي — آخر مراجعة داخلية: {esc(data["reviewed_at"])}</p>
<h1>{esc(data["title"])}</h1>
<p>{esc(data["summary"])}</p>
</header>
{sections}
<section class="panel"><h2>قائمة تحقق سريعة</h2><ul>{checklist}</ul></section>
<section class="panel"><h2>روابط داخل الموقع</h2><ul>{links}</ul></section>
<section class="panel"><h2>مصادر مؤسسية للمراجعة</h2><ul>{sources}</ul></section>
<section class="panel warning"><h2>تنبيه مهني وخصوصية</h2><p>هذه الصفحة للتثقيف العام، ولا تقدم استشارة قانونية أو أمنية أو طبية، ولا تثبت أن أداة بعينها آمنة أو معتمدة. راجع القوانين والجهات التنظيمية المحلية وسياسة الأداة نفسها قبل إدخال بيانات حساسة.</p></section>
</main>
</body>
</html>'''


def build(output_root: Path) -> dict:
    data = load_content()
    page_dir = output_root / "care-guides" / data["slug"]
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / "index.html").write_text(render_page(data), encoding="utf-8")

    sitemap = output_root / "sitemap-privacy-mental-health-tools.xml"
    sitemap.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{CANONICAL}</loc><lastmod>{data["reviewed_at"]}</lastmod></url>\n'
        '</urlset>\n',
        encoding="utf-8",
    )
    report = {
        "id": data["id"],
        "status": "built-not-published",
        "page": f"care-guides/{data['slug']}/index.html",
        "canonical": CANONICAL,
        "sources": len(data["sources"]),
        "sections": len(data["sections"]),
        "internal_links": len(data["internal_links"]),
    }
    api_dir = output_root / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "privacy-mental-health-tools-v182.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "_site"
    report = build(output)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
