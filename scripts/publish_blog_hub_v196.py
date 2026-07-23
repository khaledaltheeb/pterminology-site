from __future__ import annotations

import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
PREFIX = "/pterminology-site/"
VERSION = 196
ROUTES = [
    {
        "title": "الموسوعة النفسية",
        "href": "encyclopedia/",
        "summary": "ابدأ بالتعريف والفروق والعلامات والعوامل والأثر الوظيفي، ثم انتقل إلى المقالات التطبيقية عندما تحتاج إلى سياق أوسع.",
    },
    {
        "title": "أدلة التعامل والرعاية",
        "href": "care-guides/",
        "summary": "خطوات عملية للاستعداد للمواعيد، والتواصل مع المختص، وتنظيم الدعم اليومي، ومساندة مقدم الرعاية ضمن حدود غير تشخيصية.",
    },
    {
        "title": "النصائح العملية",
        "href": "tips/",
        "summary": "خطط قصيرة قابلة للتطبيق، وأخطاء شائعة، وجمل مساعدة، ومؤشرات لمراجعة التقدم دون وعود علاجية مطلقة.",
    },
    {
        "title": "ذوو الاحتياجات الخاصة",
        "href": "special-needs/",
        "summary": "محتوى يركز على الوصول والتواصل والبيئة والتكييف والكرامة، ولا يختزل الشخص في تشخيص أو وصف واحد.",
    },
    {
        "title": "الأسرة والطفل",
        "href": "sectors/family/",
        "summary": "موضوعات للأسرة والطفل والعلاقات والدعم المنزلي، مع إحالات إلى الأدلة المتخصصة عندما تتجاوز الحاجة النصائح العامة.",
    },
    {
        "title": "المراكز الموضوعية",
        "href": "hubs/",
        "summary": "مجموعات منظمة للمفاهيم المتقاربة تساعد على المقارنة وتقلل التنقل العشوائي بين الصفحات.",
    },
    {
        "title": "الثقة والمنهج التحريري",
        "href": "trust/",
        "summary": "سياسات المصادر والمراجعة والتصحيح والخصوصية وحدود المحتوى، وكيف تُمنع الادعاءات غير الموثقة من النشر.",
    },
]


def e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def canonical(route: str = "blog/") -> str:
    return BASE + route


def render() -> str:
    items = "".join(
        f'''<article class="card"><h2>{e(item["title"])}</h2><p>{e(item["summary"])}</p><a href="{PREFIX}{e(item["href"])}">فتح {e(item["title"])}</a></article>'''
        for item in ROUTES
    )
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "name": "البلوج النفسي العربي",
                "description": "بوابة مقالات ومسارات تفسيرية تربط المصطلحات النفسية بالأدلة العملية والأسرة وذوي الاحتياجات والمنهج التحريري.",
                "url": canonical(),
                "inLanguage": "ar",
                "isPartOf": {"@type": "WebSite", "name": "مصطلحات علم النفس", "url": BASE},
            },
            {
                "@type": "BreadcrumbList",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": BASE},
                    {"@type": "ListItem", "position": 2, "name": "البلوج", "item": canonical()},
                ],
            },
            {
                "@type": "ItemList",
                "name": "مسارات البلوج والمقالات",
                "numberOfItems": len(ROUTES),
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": index,
                        "name": item["title"],
                        "url": canonical(item["href"]),
                    }
                    for index, item in enumerate(ROUTES, start=1)
                ],
            },
        ],
    }
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>البلوج النفسي العربي | مقالات وأدلة ومسارات موثوقة</title>
<meta name="description" content="بلوج نفسي عربي منظم يربط تعريفات الموسوعة بالمقالات التفسيرية وأدلة التعامل والأسرة وذوي الاحتياجات، مع حدود واضحة تمنع التشخيص الذاتي والادعاءات غير الموثقة.">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<link rel="canonical" href="{canonical()}">
<link rel="manifest" href="{PREFIX}manifest.webmanifest">
<meta property="og:type" content="website">
<meta property="og:locale" content="ar_AR">
<meta property="og:title" content="البلوج النفسي العربي | مصطلحات علم النفس">
<meta property="og:description" content="مقالات ومسارات عربية تربط الفهم النظري بالتطبيق العملي والأسرة وذوي الاحتياجات والمنهج التحريري.">
<meta property="og:url" content="{canonical()}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="البلوج النفسي العربي | مصطلحات علم النفس">
<meta name="twitter:description" content="ابدأ من سؤال أو مفهوم، ثم انتقل إلى الموسوعة والأدلة والمسارات التطبيقية المناسبة.">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False).replace("</", "<\\/")}</script>
<style>
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#173f45;background:linear-gradient(145deg,#fff8fc,#e3faf7,#eeeaff)}}a{{color:#086e69}}a:focus-visible{{outline:3px solid #168f88;outline-offset:4px}}.skip{{position:absolute;right:-9999px;top:8px;background:#fff;padding:10px 14px;border:2px solid #168f88;border-radius:12px}}.skip:focus{{right:8px}}main{{width:min(1120px,92%);margin:auto;padding:28px 0 64px}}nav{{display:flex;gap:10px;flex-wrap:wrap}}nav a,.button{{display:inline-block;padding:10px 15px;border:1px solid #b9dfda;border-radius:14px;background:#fff;text-decoration:none;font-weight:800}}header,.card,.notice{{background:rgba(255,255,255,.96);border:1px solid #c7e8e3;border-radius:22px;box-shadow:0 16px 44px rgba(40,100,100,.09)}}header{{padding:clamp(22px,5vw,48px);margin:18px 0;background:linear-gradient(135deg,#ffe5ef,#dffaf7,#eee9ff)}}h1{{font-size:clamp(2.1rem,6vw,4.2rem);line-height:1.25;margin:.2em 0}}.lead{{font-size:1.12rem;color:#496d70;max-width:850px}}.notice{{padding:18px 22px;border-right:6px solid #c04a71;margin:18px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin:24px 0}}.card{{padding:22px;display:flex;flex-direction:column}}.card h2{{font-size:1.35rem;color:#7b3658;margin-top:0}}.card p{{color:#496d70;flex:1}}.card a{{font-weight:900}}footer{{padding:26px 0;color:#496d70}}@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
</style>
</head>
<body>
<a class="skip" href="#content">انتقل إلى المحتوى</a>
<main id="content">
<nav aria-label="التنقل الرئيسي"><a href="{PREFIX}">الرئيسية</a><a href="{PREFIX}start-here/">ابدأ من هنا</a><a href="{PREFIX}encyclopedia/">الموسوعة</a><a href="{PREFIX}care-guides/">أدلة التعامل</a><a href="{PREFIX}special-needs/">ذوو الاحتياجات</a></nav>
<header><p><strong>البلوج النفسي العربي</strong></p><h1>من التعريف إلى الفهم والتطبيق</h1><p class="lead">هذه البوابة تجمع المسارات التفسيرية للمشروع. استخدم الموسوعة عندما تبحث عن معنى المصطلح والفروق الأساسية، وانتقل إلى الأدلة والنصائح والمراكز الموضوعية عندما تحتاج إلى سياق عملي أو مقارنة أو خطوات منظمة.</p></header>
<section class="notice" role="note"><strong>حدود المحتوى:</strong> المقالات والمسارات للتثقيف والدعم العام، ولا تشخّص حالة فردية ولا تستبدل التقييم المهني. عند وجود خطر مباشر أو وشيك، تواصل مع خدمات الطوارئ المحلية أو جهة صحية عاجلة.</section>
<section aria-labelledby="paths"><h2 id="paths">مسارات القراءة الرئيسية</h2><p>اختر المسار بحسب السؤال، لا بحسب كثرة الروابط. كل بطاقة تقود إلى قسم قائم وذي وظيفة واضحة، مع تجنب تكرار التعريف نفسه في صفحات متعددة.</p><div class="grid">{items}</div></section>
<section aria-labelledby="method"><h2 id="method">كيف تستخدم البلوج بفعالية؟</h2><ol><li>ابدأ بصفحة الموسوعة لفهم الاسم الأساسي والمرادفات والفروق.</li><li>اقرأ المقال أو الدليل الذي يجيب عن حاجتك العملية بدل جمع معلومات عامة غير مترابطة.</li><li>راجع تاريخ التحديث وحالة المراجعة والمصادر عندما تكون المعلومة حساسة أو قابلة للتغير.</li><li>لا تستخدم قائمة علامات أو نتيجة أداة بوصفها تشخيصًا ذاتيًا.</li><li>انتقل إلى مركز الثقة لفهم حدود النشر والمراجعة والتصحيح.</li></ol></section>
<footer>© مصطلحات علم النفس — بوابة مقالات عربية تثقيفية منظمة.</footer>
</main>
</body>
</html>'''


def write_sitemap(site: Path) -> None:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    urlset = ET.Element(f"{{{ns}}}urlset")
    url = ET.SubElement(urlset, f"{{{ns}}}url")
    ET.SubElement(url, f"{{{ns}}}loc").text = canonical()
    ET.SubElement(url, f"{{{ns}}}changefreq").text = "weekly"
    ET.ElementTree(urlset).write(site / "sitemap-blog.xml", encoding="utf-8", xml_declaration=True)


def publish(site: Path = SITE) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")
    output = site / "blog" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(), encoding="utf-8")
    write_sitemap(site)
    report = {
        "version": VERSION,
        "status": "built-not-published",
        "route": "/blog/",
        "pathways": len(ROUTES),
        "structured_data": ["CollectionPage", "BreadcrumbList", "ItemList"],
        "sitemap": "/sitemap-blog.xml",
        "non_diagnostic": True,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "blog-hub-v196.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    publish()
