from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v182" / "audience-pathways-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
ROUTE = "/for-you/"


def esc(value: object) -> str:
    return escape(str(value), quote=True)


def render(data: dict) -> str:
    resources = {item["id"]: item for item in data["shared_resources"]}
    cards = []
    for audience in data["audiences"]:
        resource_links = "".join(
            f'<li><a href="{esc(resources[key]["href"])}">{esc(resources[key]["title"])}</a> — {esc(resources[key]["purpose"])}</li>'
            for key in audience["recommended"]
        )
        goals = "".join(f"<li>{esc(item)}</li>" for item in audience["goals"])
        steps = "".join(f"<li>{esc(item)}</li>" for item in audience["first_steps"])
        avoid = "".join(f"<li>{esc(item)}</li>" for item in audience["avoid"])
        cards.append(
            f'<article class="path" id="{esc(audience["id"])}"><h2>{esc(audience["title"])}</h2>'
            f'<p>{esc(audience["intro"])}</p><h3>ما الذي يساعدك هذا المسار عليه؟</h3><ul>{goals}</ul>'
            f'<h3>ابدأ بهذه الخطوات</h3><ol>{steps}</ol><h3>الموارد المناسبة</h3><ul>{resource_links}</ul>'
            f'<h3>تجنب</h3><ul>{avoid}</ul></article>'
        )
    canonical = f"{BASE}{ROUTE}"
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebPage", "name": data["title"], "description": data["description"], "url": canonical, "inLanguage": "ar"},
            {"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE}/"},
                {"@type": "ListItem", "position": 2, "name": "مسارات المستخدم", "item": canonical}
            ]}
        ]
    }
    principles = "".join(f"<li>{esc(item)}</li>" for item in data["principles"])
    jumps = "".join(f'<a href="#{esc(item["id"])}">{esc(item["title"])}</a>' for item in data["audiences"])
    safety = data["safety"]
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data['title'])}</title><meta name="description" content="{esc(data['description'])}"><link rel="canonical" href="{canonical}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(data['title'])}"><meta property="og:description" content="{esc(data['description'])}"><meta property="og:url" content="{canonical}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{esc(data['title'])}"><meta name="twitter:description" content="{esc(data['description'])}">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
<style>:root{{--ink:#173f45;--line:#c9e9e5;--accent:#168f88;--bg:#f7fffd}}*{{box-sizing:border-box}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.85;color:var(--ink);background:var(--bg)}}a{{color:#086e69}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:3px}}.wrap{{width:min(1100px,92%);margin:auto}}header,footer{{padding:22px 0}}main{{padding-bottom:50px}}.hero,.path,.principles,.safety{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:24px;margin:18px 0}}.hero h1{{font-size:clamp(2rem,6vw,4rem);line-height:1.25}}.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}}.path h2{{color:#7f3659}}.jump{{display:flex;gap:9px;flex-wrap:wrap}}.jump a{{background:#e8fff3;padding:8px 12px;border-radius:999px;font-weight:700;text-decoration:none}}@media(max-width:780px){{.grid{{grid-template-columns:1fr}}}}</style></head>
<body><div class="wrap"><header><a href="../">مصطلحات علم النفس</a> / مسارات المستخدم</header><main>
<section class="hero"><h1>{esc(data['title'])}</h1><p>{esc(data['description'])}</p><nav class="jump" aria-label="اختيار المسار">{jumps}</nav></section>
<section class="principles"><h2>معايير مشتركة</h2><ul>{principles}</ul></section><div class="grid">{''.join(cards)}</div>
<section class="safety" aria-labelledby="safety"><h2 id="safety">حدود السلامة</h2><p>{esc(safety['non_diagnostic'])}</p><p>{esc(safety['urgent_help'])}</p><p>{esc(safety['child_safeguarding'])}</p></section>
</main><footer><a href="../start-here/">ابدأ من هنا</a> · <a href="../encyclopedia/">الموسوعة</a> · <a href="../special-needs/">ذوو الإعاقة والاحتياجات التعليمية</a></footer></div></body></html>'''


def add_sitemap(index_path: Path, child_url: str) -> None:
    if not index_path.exists():
        index_path.write_text('<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>', encoding="utf-8")
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    tree = ET.parse(index_path)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    current = [node.text for node in root.findall("sm:sitemap/sm:loc", ns)]
    if child_url not in current:
        node = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap")
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = child_url
    tree.write(index_path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    target = SITE / "for-you" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data), encoding="utf-8")
    sitemap_name = "sitemap-audience-pathways.xml"
    (SITE / sitemap_name).write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{BASE}{ROUTE}</loc><lastmod>{data["reviewed_at"]}</lastmod></url></urlset>',
        encoding="utf-8"
    )
    add_sitemap(SITE / "sitemap.xml", f"{BASE}/{sitemap_name}")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    report = {"version": 182, "status": "built-not-published", "route": ROUTE, "audiences": len(data["audiences"]), "shared_resources": len(data["shared_resources"]), "sitemap": sitemap_name}
    (api / "audience-pathways-v182.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
