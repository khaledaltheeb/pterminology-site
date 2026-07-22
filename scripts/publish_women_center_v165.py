from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content" / "v165" / "women-mental-health-ar.json"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site/"


def e(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_sections(items: list[dict[str, str]]) -> str:
    return "".join(
        f'<section><h2>{e(item["title"])}</h2><p>{e(item["body"])}</p></section>'
        for item in items
    )


def render_sources(items: list[dict[str, str]]) -> str:
    rows = "".join(
        f'<li><a href="{e(item["url"])}" rel="noopener">{e(item["title"])}</a>'
        f' — تحقق {e(item["verified_at"])}</li>'
        for item in items
    )
    return f"<section><h2>المصادر</h2><ul>{rows}</ul></section>"


def page_shell(title: str, description: str, canonical: str, body: str, schema: dict) -> str:
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | مصطلحات علم النفس</title><meta name="description" content="{e(description)}"><link rel="canonical" href="{e(canonical)}"><meta name="robots" content="index,follow,max-image-preview:large"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(canonical)}"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(description)}"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script><style>*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:#f6fbfa}}main{{width:min(1000px,94%);margin:auto;padding:24px 0 64px}}nav,header,section{{background:#fff;border:1px solid #c9e1dc;border-radius:20px;padding:clamp(18px,4vw,32px);margin:16px 0}}nav{{display:flex;gap:10px;flex-wrap:wrap}}a{{color:#075e59}}h1{{font-size:clamp(2rem,5vw,3.2rem);line-height:1.35}}h2{{color:#713953}}.notice{{border-right:6px solid #a33860;background:#fff5f8}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}}.card{{border:1px solid #c9e1dc;border-radius:16px;padding:16px}}:focus-visible{{outline:3px solid #1b6cff;outline-offset:3px}}@media(max-width:600px){{nav{{display:grid}}}}@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important;transition:none!important}}}}</style></head><body><main><nav aria-label="التنقل"><a href="/pterminology-site/">الرئيسية</a><a href="/pterminology-site/encyclopedia/">الموسوعة</a><a href="/pterminology-site/women/">صحة المرأة النفسية</a></nav>{body}</main></body></html>'''


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def update_sitemap(urls: list[str]) -> None:
    sitemap = SITE / "sitemap-women.xml"
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{namespace}}}url")
        ET.SubElement(node, f"{{{namespace}}}loc").text = url
    ET.ElementTree(root).write(sitemap, encoding="utf-8", xml_declaration=True)

    index = SITE / "sitemap.xml"
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")
    reference = BASE + "sitemap-women.xml"
    if reference in text:
        return
    if "</sitemapindex>" in text:
        text = text.replace(
            "</sitemapindex>",
            f"<sitemap><loc>{reference}</loc></sitemap></sitemapindex>",
            1,
        )
    elif "</urlset>" in text:
        entries = "".join(f"<url><loc>{url}</loc></url>" for url in urls)
        text = text.replace("</urlset>", entries + "</urlset>", 1)
    else:
        raise SystemExit("Unsupported sitemap root")
    index.write_text(text, encoding="utf-8")


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    center = data["center"]
    pillar = data["pillar"]
    center_url = BASE + "women/"
    pillar_url = BASE + "women/perinatal-mental-health/"

    cards = "".join(
        f'<article class="card"><h3>{e(topic["title"])}</h3><p>{e(topic["description"])}</p>'
        + (
            f'<a href="{e(topic["href"])}">اقرئي الدليل</a>'
            if topic.get("href")
            else "<p><strong>قيد الإعداد المنهجي</strong></p>"
        )
        + "</article>"
        for topic in center["topics"]
    )
    center_body = (
        f'<header><p>مرجع عربي متخصص</p><h1>{e(center["title_ar"])}</h1>'
        f'<p>{e(center["summary"])}</p><p>آخر مراجعة داخلية: {e(center["reviewed_at"])}'
        " — الحالة: يحتاج مراجعة اختصاصية خارجية.</p></header>"
        '<section class="notice"><h2>حدود مهنية</h2><p>المحتوى للتثقيف ولا يشخّص حالة '
        "ولا يحدد سبب الأعراض ولا يوصي ببدء دواء أو إيقافه. عند خطر مباشر استخدمي خدمات "
        "الطوارئ المحلية.</p></section>"
        + render_sections(center["sections"])
        + f'<section><h2>مسارات متخصصة</h2><div class="cards">{cards}</div></section>'
        + render_sources(center["sources"])
    )
    center_schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": center["title_ar"],
        "description": center["summary"],
        "url": center_url,
        "inLanguage": "ar",
        "dateModified": center["reviewed_at"],
        "isPartOf": {"@type": "WebSite", "name": "مصطلحات علم النفس", "url": BASE},
    }

    pillar_body = (
        f'<header><p>دليل عملي غير تشخيصي</p><h1>{e(pillar["title_ar"])}</h1>'
        f'<p>{e(pillar["summary"])}</p><p>آخر مراجعة داخلية: {e(pillar["reviewed_at"])}'
        " — الحالة: يحتاج مراجعة اختصاصية خارجية.</p></header>"
        '<section class="notice"><h2>تنبيه سلامة</h2><p>الذهان بعد الولادة أو وجود نية '
        "لإيذاء النفس أو الطفل أو ارتباك شديد حالات تستلزم مساعدة طبية عاجلة. لا تتركي الشخص "
        "وحده عند وجود خطر مباشر.</p></section>"
        + render_sections(pillar["sections"])
        + render_sources(pillar["sources"])
    )
    pillar_schema = {
        "@context": "https://schema.org",
        "@type": "MedicalWebPage",
        "name": pillar["title_ar"],
        "description": pillar["summary"],
        "url": pillar_url,
        "inLanguage": "ar",
        "dateModified": pillar["reviewed_at"],
        "lastReviewed": pillar["reviewed_at"],
        "about": [
            {"@type": "MedicalCondition", "name": "Perinatal depression"},
            {"@type": "MedicalCondition", "name": "Perinatal anxiety"},
        ],
        "isPartOf": {"@type": "CollectionPage", "name": center["title_ar"], "url": center_url},
    }

    write(
        SITE / "women" / "index.html",
        page_shell(center["title_ar"], center["summary"], center_url, center_body, center_schema),
    )
    write(
        SITE / "women" / "perinatal-mental-health" / "index.html",
        page_shell(pillar["title_ar"], pillar["summary"], pillar_url, pillar_body, pillar_schema),
    )
    update_sitemap([center_url, pillar_url])

    homepage = SITE / "index.html"
    if homepage.exists():
        text = homepage.read_text(encoding="utf-8")
        if "/pterminology-site/women/" not in text:
            card = (
                '<section aria-labelledby="women-center-title"><h2 id="women-center-title">'
                "الصحة النفسية للمرأة</h2><p>مسارات متخصصة عبر مراحل الحياة، تبدأ بالحمل وما "
                'بعد الولادة، بمحتوى آمن وغير تشخيصي.</p><p><a href="/pterminology-site/women/">'
                "زيارة مركز صحة المرأة النفسية</a></p></section>"
            )
            text = text.replace("</main>", card + "</main>", 1)
            homepage.write_text(text, encoding="utf-8")

    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    report = {
        "version": 165,
        "pages": 2,
        "center": center_url,
        "pillar": pillar_url,
        "sources": len(center["sources"]) + len(pillar["sources"]),
        "review_status": "needs-specialist-review",
        "sitemap": "sitemap-women.xml",
    }
    (api / "women-center-v165.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
