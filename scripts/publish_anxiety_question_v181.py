#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content/publishers/questions/anxiety-normal-or-needs-assessment-v181.json"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_page(data: dict) -> str:
    route = data["route"]
    canonical = data["canonical"]
    faq_entities = [
        {
            "@type": "Question",
            "name": item["question"],
            "acceptedAnswer": {"@type": "Answer", "text": item["answer"]},
        }
        for item in data["faq"]
    ]
    schemas = [
        {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": data["title"],
            "description": data["description"],
            "url": canonical,
            "inLanguage": "ar",
            "dateModified": data["reviewed_at"],
            "isPartOf": {
                "@type": "WebSite",
                "name": "مصطلحات علم النفس",
                "url": "https://khaledaltheeb.github.io/pterminology-site/",
            },
        },
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": faq_entities,
        },
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": "https://khaledaltheeb.github.io/pterminology-site/"},
                {"@type": "ListItem", "position": 2, "name": "الأسئلة", "item": "https://khaledaltheeb.github.io/pterminology-site/questions/"},
                {"@type": "ListItem", "position": 3, "name": data["title"], "item": canonical},
            ],
        },
    ]
    sections = []
    for section in data["sections"]:
        paragraphs = "\n".join(f"<p>{esc(p)}</p>" for p in section["paragraphs"])
        sections.append(f'<section><h2>{esc(section["heading"])}</h2>{paragraphs}</section>')
    faqs = "\n".join(
        f'<details><summary>{esc(item["question"])}</summary><p>{esc(item["answer"])}</p></details>'
        for item in data["faq"]
    )
    links = "\n".join(
        f'<li><a href="{esc(item["href"])}">{esc(item["label"])}</a></li>'
        for item in data["internal_links"]
    )
    sources = "\n".join(
        f'<li><a href="{esc(item["url"])}" rel="noopener noreferrer">{esc(item["organization"])} — {esc(item["title"])}</a> <span>({esc(item["published_at"])})</span></li>'
        for item in data["sources"]
    )
    schema_json = "\n".join(
        f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'
        for schema in schemas
    )
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data["meta_title"])}</title>
<meta name="description" content="{esc(data["description"])}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:locale" content="ar_AR">
<meta property="og:title" content="{esc(data["meta_title"])}">
<meta property="og:description" content="{esc(data["description"])}">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(data["meta_title"])}">
<meta name="twitter:description" content="{esc(data["description"])}">
{schema_json}
<style>
:root{{font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;line-height:1.85;color:#172526;background:#f7f5ef}}
body{{margin:0}}main{{max-width:860px;margin:auto;padding:1.25rem}}article{{background:#fff;padding:clamp(1rem,3vw,2.2rem);border-radius:1rem;box-shadow:0 8px 28px #0001}}h1{{font-size:clamp(1.9rem,5vw,3rem);line-height:1.25}}h2{{margin-top:2rem;color:#145c59}}.answer{{border-inline-start:.35rem solid #b58a3c;padding:1rem;background:#faf6e9;font-size:1.08rem}}.notice{{padding:1rem;background:#eef6f5;border-radius:.7rem}}a{{color:#075f6b}}summary{{font-weight:700;cursor:pointer;padding:.5rem 0}}footer{{margin-top:2rem;border-top:1px solid #ddd;padding-top:1rem}}.skip{{position:absolute;inset-inline-start:-9999px}}.skip:focus{{position:static;display:inline-block;padding:.5rem;background:#fff}}
@media print{{body{{background:#fff}}article{{box-shadow:none}}nav,.skip{{display:none}}}}
</style>
</head>
<body>
<a class="skip" href="#content">تجاوز إلى المحتوى</a>
<main id="content">
<article>
<nav aria-label="مسار التنقل"><a href="/">الرئيسية</a> ← <a href="/questions/">الأسئلة</a></nav>
<h1>{esc(data["title"])}</h1>
<p class="answer"><strong>الإجابة المباشرة:</strong> {esc(data["short_answer"])}</p>
<div class="notice" role="note"><strong>حدود الصفحة:</strong> هذه مادة تثقيفية لا تشخّص اضطراب القلق، ولا تحدد علاجًا أو دواءً فرديًا. الأعراض الجديدة أو الشديدة أو الخطر الفوري تحتاج مساعدة مهنية مناسبة.</div>
{''.join(sections)}
<section><h2>أسئلة شائعة</h2>{faqs}</section>
<section><h2>مسارات مرتبطة</h2><ul>{links}</ul></section>
<footer><h2>المصادر المؤسسية</h2><ul>{sources}</ul><p>آخر مراجعة داخلية: {esc(data["reviewed_at"])}. الحالة: تحتاج مراجعة اختصاصية قبل أي ادعاء اعتماد خارجي.</p></footer>
</article>
</main>
</body>
</html>'''


def publish(site_dir: Path) -> dict:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    output = site_dir / data["route"].strip("/") / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_page(data), encoding="utf-8")
    sitemap = site_dir / "sitemap-questions.xml"
    sitemap.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{html.escape(data["canonical"])}</loc><lastmod>{data["reviewed_at"]}</lastmod></url>\n'
        '</urlset>\n',
        encoding="utf-8",
    )
    report = {
        "publisher": data["publisher_id"],
        "item_id": data["item_id"],
        "route": data["route"],
        "state": "built-not-published",
        "page": output.relative_to(site_dir).as_posix(),
        "sitemap": sitemap.name,
        "source_count": len(data["sources"]),
        "live_verified": False,
    }
    api = site_dir / "api" / "publisher-07-question-v181.json"
    api.parent.mkdir(parents=True, exist_ok=True)
    api.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-dir", type=Path, default=ROOT / "_site")
    args = parser.parse_args()
    report = publish(args.site_dir)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
