from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v160" / "blog-anxiety-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
CSS = """*{box-sizing:border-box}body{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:#f7fbfb}main{width:min(980px,92%);margin:auto;padding:24px 0 64px}header,article,section{background:#fff;border:1px solid #c9e9e5;border-radius:20px;padding:clamp(18px,4vw,34px);margin:16px 0}nav{display:flex;gap:10px;flex-wrap:wrap}a{color:#086e69;font-weight:700}h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.35}h2{color:#7f3659;margin-top:1.8em}.meta,.note{color:#496d70}.note{border-right:5px solid #b9537d;background:#fff2f7;padding:14px;border-radius:12px}.cards{display:grid;gap:14px}.card{border:1px solid #c9e9e5;border-radius:16px;padding:18px;background:#f9fffe}:focus-visible{outline:3px solid #168f88;outline-offset:3px}@media print{nav{display:none}body{background:#fff}header,article,section{border:0;padding:0}}"""

def e(value: object) -> str:
    return html.escape(str(value), quote=True)

def write_page(path: Path, title: str, description: str, canonical: str, body: str, schema: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    script = json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")
    page = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | مصطلحات علم النفس</title><meta name="description" content="{e(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1"><link rel="canonical" href="{e(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(canonical)}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{script}</script><style>{CSS}</style></head><body><main><nav aria-label="التنقل"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}blog/">المدونة</a><a href="{BASE_PATH}encyclopedia/">الموسوعة</a><a href="{BASE_PATH}daily-tools/">الأدوات اليومية</a></nav>{body}</main><script>if('serviceWorker' in navigator){{window.addEventListener('load',()=>navigator.serviceWorker.register('{BASE_PATH}sw.js'));}}</script></body></html>'''
    path.write_text(page, encoding="utf-8")

def add_sitemap(urls: list[str], lastmod: str) -> None:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    root = ET.Element(f"{{{ns}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = lastmod
    ET.ElementTree(root).write(SITE / "sitemap-blog.xml", encoding="utf-8", xml_declaration=True)
    index = SITE / "sitemap.xml"
    if not index.exists(): return
    tree = ET.parse(index); current = tree.getroot(); tag = current.tag.rsplit("}", 1)[-1]
    target = BASE + "sitemap-blog.xml"
    if tag == "sitemapindex":
        existing = {loc.text for loc in current.iter(f"{{{ns}}}loc")}
        if target not in existing:
            node = ET.SubElement(current, f"{{{ns}}}sitemap"); ET.SubElement(node, f"{{{ns}}}loc").text = target; tree.write(index, encoding="utf-8", xml_declaration=True)

def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8")); articles = payload["articles"]; cards=[]; urls=[BASE+"blog/"]
    for article in articles:
        slug=article["slug"]; canonical=BASE+f"blog/{slug}/"; urls.append(canonical)
        sections="".join(f'<section><h2>{e(s["heading"])}</h2>'+"".join(f'<p>{e(p)}</p>' for p in s["paragraphs"])+"</section>" for s in article["sections"])
        related="".join(f'<li><a href="{e(i["href"])}">{e(i["label"])}</a></li>' for i in article["related"])
        sources="".join(f'<li><a href="{e(s["url"])}" rel="external noopener noreferrer">{e(s["publisher"])} — {e(s["title"])}</a> ({e(s["year"])})</li>' for s in article["sources"])
        body=f'<article><p class="meta">{e(article["category"])} · {article["reading_minutes"]} دقائق قراءة · تحديث تحريري {e(article["reviewed_at"])}</p><h1>{e(article["title"])}</h1><p>{e(article["description"])}</p><p class="note">محتوى تثقيفي غير تشخيصي، وحالته الحالية تحتاج مراجعة اختصاصية خارجية قبل وصفه بأنه مراجَع سريريًا.</p>{sections}<section><h2>روابط مرتبطة</h2><ul>{related}</ul></section><section><h2>المصادر</h2><ul>{sources}</ul></section></article>'
        schema={"@context":"https://schema.org","@graph":[{"@type":"BlogPosting","headline":article["title"],"description":article["description"],"inLanguage":"ar","datePublished":"2026-07-23","dateModified":article["reviewed_at"],"mainEntityOfPage":canonical,"author":{"@type":"Organization","name":"مصطلحات علم النفس","url":BASE},"citation":[s["url"] for s in article["sources"]]},{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"الرئيسية","item":BASE},{"@type":"ListItem","position":2,"name":"المدونة","item":BASE+"blog/"},{"@type":"ListItem","position":3,"name":article["title"],"item":canonical}]}]}
        write_page(SITE/"blog"/slug/"index.html",article["title"],article["description"],canonical,body,schema)
        cards.append(f'<article class="card"><h2><a href="{BASE_PATH}blog/{e(slug)}/">{e(article["title"])}</a></h2><p>{e(article["description"])}</p><p class="meta">{e(article["category"])} · {article["reading_minutes"]} دقائق</p></article>')
    c=payload["collection"]; index_body=f'<header><h1>{e(c["title"])}</h1><p>{e(c["description"])}</p><p class="meta">حالة المراجعة: تحتاج مراجعة اختصاصية خارجية · تحديث {e(c["reviewed_at"])}</p></header><section class="cards">{"".join(cards)}</section>'
    write_page(SITE/"blog"/"index.html",c["title"],c["description"],BASE+"blog/",index_body,{"@context":"https://schema.org","@type":"Blog","name":c["title"],"description":c["description"],"inLanguage":"ar","url":BASE+"blog/"})
    add_sitemap(urls,c["reviewed_at"]); api=SITE/"api"; api.mkdir(parents=True,exist_ok=True)
    (api/"blog-v160.json").write_text(json.dumps({"version":160,"articles":len(articles),"urls":urls,"review_status":c["review_status"],"source_count":sum(len(a["sources"]) for a in articles)},ensure_ascii=False,indent=2),encoding="utf-8")

if __name__ == "__main__": main()
