from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v75" / "blog-anxiety-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"

CSS = """*{box-sizing:border-box}body{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:#f7fbfb}main{width:min(980px,92%);margin:auto;padding:24px 0 64px}header,article,section{background:#fff;border:1px solid #c9e9e5;border-radius:20px;padding:clamp(18px,4vw,34px);margin:16px 0}nav{display:flex;gap:10px;flex-wrap:wrap}a{color:#086e69;font-weight:700}h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.35}h2{color:#7f3659;margin-top:1.8em}.meta,.note{color:#496d70}.note{border-right:5px solid #b9537d;background:#fff2f7;padding:14px;border-radius:12px}.cards{display:grid;gap:14px}.card{border:1px solid #c9e9e5;border-radius:16px;padding:18px;background:#f9fffe}:focus-visible{outline:3px solid #168f88;outline-offset:3px}@media print{nav{display:none}body{background:#fff}header,article,section{border:0;padding:0}}"""


def e(value: str) -> str:
    return html.escape(value, quote=True)


def write_page(path: Path, title: str, description: str, canonical: str, body: str, schema: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | مصطلحات علم النفس</title><meta name="description" content="{e(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{e(canonical)}"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(canonical)}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script><style>{CSS}</style></head><body><main><nav aria-label="التنقل"><a href="/pterminology-site/">الرئيسية</a><a href="/pterminology-site/blog/">المدونة</a><a href="/pterminology-site/encyclopedia/">الموسوعة</a></nav>{body}</main></body></html>'''
    path.write_text(page, encoding="utf-8")


def add_to_sitemap(urls: list[str]) -> None:
    sitemap = SITE / "sitemap-blog.xml"
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = "2026-07-22"
    ET.ElementTree(root).write(sitemap, encoding="utf-8", xml_declaration=True)

    index = SITE / "sitemap.xml"
    if not index.exists():
        return
    tree = ET.parse(index)
    current = tree.getroot()
    tag = current.tag.rsplit("}", 1)[-1]
    if tag == "sitemapindex":
        existing = {loc.text for loc in current.iter(f"{{{ns}}}loc")}
        target = BASE + "sitemap-blog.xml"
        if target not in existing:
            node = ET.SubElement(current, f"{{{ns}}}sitemap")
            ET.SubElement(node, f"{{{ns}}}loc").text = target
            tree.write(index, encoding="utf-8", xml_declaration=True)


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    articles = payload["articles"]
    cards = []
    urls = [BASE + "blog/"]
    for article in articles:
        slug = article["slug"]
        canonical = BASE + f"blog/{slug}/"
        urls.append(canonical)
        sections = "".join(f'<section><h2>{e(section["heading"])}</h2>' + "".join(f'<p>{e(p)}</p>' for p in section["paragraphs"]) + "</section>" for section in article["sections"])
        related = "".join(f'<li><a href="{e(item["href"])}">{e(item["label"])}</a></li>' for item in article["related"])
        sources = "".join(f'<li><a href="{e(source["url"])}" rel="external noopener">{e(source["title"])}</a> — تم الاطلاع {e(source["accessed_at"])}</li>' for source in article["sources"])
        body = f'<article><p class="meta">{e(article["category"])} · {article["reading_minutes"]} دقائق قراءة · آخر مراجعة {e(article["reviewed_at"])}</p><h1>{e(article["title"])}</h1><p>{e(article["description"])}</p><p class="note">هذا المقال للتثقيف العام، ولا يشخّص حالة فردية ولا يوصي بتغيير دواء أو علاج دون مختص.</p>{sections}<section><h2>روابط مرتبطة</h2><ul>{related}</ul></section><section><h2>المصادر</h2><ul>{sources}</ul></section></article>'
        schema = {"@context":"https://schema.org","@graph":[{"@type":"BlogPosting","headline":article["title"],"description":article["description"],"inLanguage":"ar","datePublished":"2026-07-22","dateModified":article["reviewed_at"],"mainEntityOfPage":canonical,"author":{"@type":"Organization","name":"مصطلحات علم النفس"},"citation":[s["url"] for s in article["sources"]]},{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"الرئيسية","item":BASE},{"@type":"ListItem","position":2,"name":"المدونة","item":BASE+"blog/"},{"@type":"ListItem","position":3,"name":article["title"],"item":canonical}]}]}
        write_page(SITE / "blog" / slug / "index.html", article["title"], article["description"], canonical, body, schema)
        cards.append(f'<article class="card"><h2><a href="/pterminology-site/blog/{e(slug)}/">{e(article["title"])}</a></h2><p>{e(article["description"])}</p><p class="meta">{e(article["category"])} · {article["reading_minutes"]} دقائق</p></article>')
    collection = payload["collection"]
    index_body = f'<header><h1>{e(collection["title"])}</h1><p>{e(collection["description"])}</p><p class="meta">آخر مراجعة {e(collection["reviewed_at"])}</p></header><section class="cards">{"".join(cards)}</section>'
    write_page(SITE / "blog" / "index.html", collection["title"], collection["description"], BASE+"blog/", index_body, {"@context":"https://schema.org","@type":"Blog","name":collection["title"],"description":collection["description"],"inLanguage":"ar","url":BASE+"blog/"})
    add_to_sitemap(urls)
    api = SITE / "api"; api.mkdir(parents=True, exist_ok=True)
    (api / "blog-v75.json").write_text(json.dumps({"version":75,"articles":len(articles),"urls":urls,"reviewed":all(a["status"]=="reviewed" for a in articles)}, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
