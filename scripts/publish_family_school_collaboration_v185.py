from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v185" / "family-school-collaboration-ar.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site"
BASE_PATH = "/pterminology-site/"


def e(value: object) -> str:
    return escape(str(value), quote=True)


def validate(data: dict) -> None:
    required = {"slug", "title", "description", "status", "reviewed_at", "professional_limits", "principles", "meeting_steps", "communication_template", "do_not_do", "sources"}
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing fields: {sorted(missing)}")
    if data["status"] != "internally-reviewed":
        raise SystemExit("Unexpected review status")
    if len(data["principles"]) < 5 or len(data["meeting_steps"]) < 7 or len(data["sources"]) < 3:
        raise SystemExit("Guide depth is insufficient")
    if any(not source["url"].startswith("https://") for source in data["sources"]):
        raise SystemExit("All sources must use HTTPS")
    joined = json.dumps(data, ensure_ascii=False)
    for forbidden in ["تشخيص نهائي", "شفاء مضمون", "غيّر الدواء", "أوقف الدواء"]:
        if forbidden in joined:
            raise SystemExit(f"Forbidden claim: {forbidden}")


def head(data: dict, canonical: str, title: str, description: str, schema_type: str) -> str:
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": schema_type,
                "name": title,
                "description": description,
                "url": canonical,
                "inLanguage": "ar",
                "dateModified": data["reviewed_at"],
                "citation": [source["url"] for source in data["sources"]],
                "isPartOf": {"@type": "WebSite", "name": "مصطلحات علم النفس", "url": BASE + "/"},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE + "/"},
                    {"@type": "ListItem", "position": 2, "name": "ذوو الاحتياجات الخاصة", "item": BASE + "/special-needs/"},
                    {"@type": "ListItem", "position": 3, "name": title, "item": canonical},
                ],
            },
        ],
    }
    css = """
    :root{--ink:#173f45;--muted:#4b6e71;--line:#c7e8e3;--accent:#08776e;--accent2:#8b3f64;--pink:#fff0f6;--mint:#eafff5;--turq:#e7fbf8;--white:#fff}
    *{box-sizing:border-box}body{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:var(--ink);background:linear-gradient(145deg,#fff9fc,var(--turq),#f0edff)}a{color:#086e69}.wrap{width:min(1120px,92%);margin:auto}.skip{position:absolute;right:-9999px}.skip:focus{right:8px;top:8px;background:#fff;padding:10px}.nav,.actions{display:flex;gap:10px;flex-wrap:wrap}.nav a,.button{padding:10px 14px;border:1px solid #7fb8b1;border-radius:12px;background:#fff;text-decoration:none;font-weight:800}header,section,article{background:rgba(255,255,255,.96);border:1px solid var(--line);border-radius:20px;padding:clamp(18px,4vw,32px);margin:16px 0}header{background:linear-gradient(135deg,var(--pink),var(--turq))}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.3}h2{color:var(--accent2)}h3{color:var(--accent)}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}.notice{border-right:6px solid var(--accent2);background:var(--pink)}.worksheet{background:#fff}.field{border:1px dashed #6ea9a2;border-radius:12px;padding:14px;margin:12px 0}.lines{height:5rem;background:repeating-linear-gradient(to bottom,transparent 0,transparent 1.55rem,#bfdad6 1.58rem,#bfdad6 1.62rem)}@media(max-width:800px){.grid{grid-template-columns:1fr}.nav{display:grid}}@media print{.nav,.skip,.no-print{display:none!important}body{background:#fff}header,section,article{box-shadow:none;break-inside:avoid}.worksheet{border:0}}
    """
    return f'''<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>{e(title)}</title><meta name="description" content="{e(description)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{e(canonical)}"><link rel="manifest" href="{BASE_PATH}manifest.webmanifest"><meta property="og:type" content="article"><meta property="og:locale" content="ar_AR"><meta property="og:url" content="{e(canonical)}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script><style>{css}</style></head>'''


def nav() -> str:
    return f'''<nav class="nav" aria-label="التنقل الرئيسي"><a href="{BASE_PATH}">الرئيسية</a><a href="{BASE_PATH}start-here/">ابدأ من هنا</a><a href="{BASE_PATH}audiences/family/">مسار الأسرة</a><a href="{BASE_PATH}audiences/teacher/">مسار المعلم</a><a href="{BASE_PATH}special-needs/">ذوو الاحتياجات الخاصة</a><a href="{BASE_PATH}resources/worksheets/">أوراق العمل</a></nav>'''


def source_list(data: dict) -> str:
    return "<ul>" + "".join(f'<li><a href="{e(s["url"])}" rel="noopener noreferrer">{e(s["publisher"])} — {e(s["title"])}</a> <small>تحقق: {e(s["verified_at"])}</small></li>' for s in data["sources"]) + "</ul>"


def render_guide(data: dict) -> str:
    canonical = BASE + f'/special-needs/{data["slug"]}/'
    principles = "".join(f'<article><h2>{e(item["title"])}</h2><p>{e(item["body"])}</p></article>' for item in data["principles"])
    steps = "".join(f"<li>{e(item)}</li>" for item in data["meeting_steps"])
    avoid = "".join(f"<li>{e(item)}</li>" for item in data["do_not_do"])
    template = data["communication_template"]
    template_html = "".join(f'<h3>{e(label)}</h3><p>{e(value)}</p>' for label, value in template.items())
    body = f'''<header><p><strong>دليل عملي للأسرة والمدرسة</strong></p><h1>{e(data["title"])}</h1><p>{e(data["description"])}</p><p><strong>آخر مراجعة:</strong> <time datetime="{e(data["reviewed_at"])}">{e(data["reviewed_at"])}</time></p></header><section class="notice"><h2>الحدود المهنية</h2><p>{e(data["professional_limits"])}</p></section><section><h2>مبادئ التعاون</h2><div class="grid">{principles}</div></section><section><h2>خطوات اجتماع قصير وفعّال</h2><ol>{steps}</ol></section><section><h2>قالب تواصل واضح</h2>{template_html}</section><section><h2>ممارسات يجب تجنبها</h2><ul>{avoid}</ul></section><section><h2>ورقة العمل</h2><p><a class="button" href="{BASE_PATH}resources/worksheets/family-school-collaboration/">فتح الورقة القابلة للطباعة</a></p></section><section><h2>المصادر</h2>{source_list(data)}</section>'''
    return f'<!doctype html><html lang="ar" dir="rtl">{head(data, canonical, data["title"] + " | مصطلحات علم النفس", data["description"], "Article")}<body><a class="skip" href="#main">انتقل إلى المحتوى</a><div class="wrap">{nav()}<main id="main">{body}</main><footer><p>محتوى تثقيفي وتنظيمي، لا يستبدل الخدمات المحلية المتخصصة.</p></footer></div></body></html>'


def render_worksheet(data: dict) -> str:
    canonical = BASE + "/resources/worksheets/family-school-collaboration/"
    prompts = ["الحاجز المحدد الذي نريد فهمه", "مثال من المنزل", "مثال من المدرسة", "ما قاله الطالب أو أشار إليه", "التكييف الذي سنجربه", "المسؤول عن التنفيذ", "مؤشر التقدم", "موعد المراجعة"]
    fields = "".join(f'<div class="field"><h2>{e(item)}</h2><div class="lines" aria-hidden="true"></div></div>' for item in prompts)
    body = f'''<header><p><strong>ورقة عمل قابلة للطباعة</strong></p><h1>خطة تعاون الأسرة والمدرسة</h1><p>استخدمها لتنظيم اجتماع واحد حول حاجز محدد، لا لتشخيص الطالب أو تقييم قيمته أو قدرته.</p></header><section class="worksheet">{fields}</section><section class="notice"><h2>تذكير</h2><p>{e(data["professional_limits"])}</p></section><p class="no-print"><button class="button" onclick="window.print()">طباعة أو حفظ PDF</button></p>'''
    return f'<!doctype html><html lang="ar" dir="rtl">{head(data, canonical, "ورقة تعاون الأسرة والمدرسة | مصطلحات علم النفس", "ورقة عربية قابلة للطباعة لتنظيم التعاون بين الأسرة والمدرسة حول حاجز محدد وتكييف قابل للقياس مع حماية خصوصية الطالب.", "LearningResource")}<body><a class="skip" href="#main">انتقل إلى المحتوى</a><div class="wrap">{nav()}<main id="main">{body}</main></div></body></html>'


def patch(path: Path, marker: str, html: str, before: str = "</main>") -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    if before not in text:
        raise SystemExit(f"Missing insertion marker in {path}")
    path.write_text(text.replace(before, html + before, 1), encoding="utf-8")
    return True


def write_sitemap(data: dict) -> int:
    urls = [BASE + f'/special-needs/{data["slug"]}/', BASE + "/resources/worksheets/family-school-collaboration/"]
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    child = SITE / "sitemap-family-school-collaboration.xml"
    root = ET.Element(f"{{{ns}}}urlset")
    for url in urls:
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = data["reviewed_at"]
    ET.ElementTree(root).write(child, encoding="utf-8", xml_declaration=True)
    main = SITE / "sitemap.xml"
    if main.is_file():
        tree = ET.parse(main); main_root = tree.getroot(); local = main_root.tag.rsplit("}", 1)[-1]
        if local == "sitemapindex":
            target = BASE + "/sitemap-family-school-collaboration.xml"
            existing = {n.text for n in main_root.findall(f"{{{ns}}}sitemap/{{{ns}}}loc") if n.text}
            if target not in existing:
                entry = ET.SubElement(main_root, f"{{{ns}}}sitemap"); ET.SubElement(entry, f"{{{ns}}}loc").text = target
        elif local == "urlset":
            existing = {n.text for n in main_root.findall(f"{{{ns}}}url/{{{ns}}}loc") if n.text}
            for url in urls:
                if url not in existing:
                    entry = ET.SubElement(main_root, f"{{{ns}}}url"); ET.SubElement(entry, f"{{{ns}}}loc").text = url
        else:
            raise SystemExit("Unsupported sitemap root")
        tree.write(main, encoding="utf-8", xml_declaration=True)
    return len(urls)


def main() -> None:
    if not SITE.is_dir():
        raise SystemExit(f"Missing site output: {SITE}")
    data = json.loads(DATA.read_text(encoding="utf-8")); validate(data)
    guide = SITE / "special-needs" / data["slug"] / "index.html"; guide.parent.mkdir(parents=True, exist_ok=True); guide.write_text(render_guide(data), encoding="utf-8")
    worksheet = SITE / "resources" / "worksheets" / "family-school-collaboration" / "index.html"; worksheet.parent.mkdir(parents=True, exist_ok=True); worksheet.write_text(render_worksheet(data), encoding="utf-8")
    link = f'<section data-family-school-v185><h2>تعاون الأسرة والمدرسة</h2><p>خطة مشتركة لتحديد الحاجز وتجربة تكييف ومراجعة أثره دون وصم.</p><a href="{BASE_PATH}special-needs/{e(data["slug"])}/">فتح الدليل</a></section>'
    patched = {
        "special_needs": patch(SITE / "special-needs" / "index.html", "data-family-school-v185", link),
        "family_audience": patch(SITE / "audiences" / "family" / "index.html", "data-family-school-v185", link),
        "teacher_audience": patch(SITE / "audiences" / "teacher" / "index.html", "data-family-school-v185", link),
    }
    count = write_sitemap(data)
    api = SITE / "api"; api.mkdir(parents=True, exist_ok=True)
    report = {"version": 185, "status": "built-not-published", "generated_pages": [str(guide.relative_to(SITE)), str(worksheet.relative_to(SITE))], "sitemap_urls": count, "patched": patched, "review_status": data["status"]}
    (api / "family-school-collaboration-v185.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
