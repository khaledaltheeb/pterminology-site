from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content" / "v34" / "arabic_sign_basics.json"
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE = "https://khaledaltheeb.github.io/pterminology-site"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def ul(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def page(*, title: str, description: str, canonical: str, body: str, page_type: str = "Article") -> str:
    structured = {
        "@context": "https://schema.org",
        "@type": page_type,
        "name": title,
        "description": description,
        "inLanguage": "ar",
        "url": canonical,
        "dateModified": "2026-07-21",
        "isAccessibleForFree": True,
    }
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | مصطلحات علم النفس</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{esc(canonical)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(structured, ensure_ascii=False)}</script>
<style>
:root{{font-family:system-ui,-apple-system,"Segoe UI",Tahoma,sans-serif;line-height:1.9;color:#17202a;background:#f7f8f9}}
body{{margin:0}}a{{color:#075985}}a:focus,button:focus{{outline:3px solid #f59e0b;outline-offset:3px}}
.skip{{position:absolute;right:-9999px}}.skip:focus{{right:1rem;top:1rem;background:#fff;padding:.7rem;z-index:9}}
header,main,footer{{max-width:900px;margin:auto;padding:1rem 1.25rem}}header{{background:#0f4c5c;color:#fff;max-width:none}}
header>div{{max-width:900px;margin:auto}}nav a{{color:#fff;margin-left:1rem}}section,.card{{background:#fff;border:1px solid #d8dee4;border-radius:12px;padding:1rem 1.2rem;margin:1rem 0}}
h1{{line-height:1.4}}h2{{margin-top:1.6rem}}.notice{{border-right:5px solid #d97706;background:#fff7ed;padding:1rem}}
.safety{{border-right:5px solid #b91c1c;background:#fef2f2;padding:1rem}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem}}
label{{display:block;margin:.5rem 0}}@media print{{header nav,.skip,.no-print{{display:none}}body{{background:#fff}}section,.card{{border:0;break-inside:avoid}}a{{color:#000;text-decoration:none}}}}
</style>
</head>
<body>
<a class="skip" href="#main">تجاوز إلى المحتوى</a>
<header><div><strong>مركز الصم وضعاف السمع</strong><nav aria-label="التنقل"><a href="{BASE}/special-education/deaf-and-hard-of-hearing/">المركز</a><a href="{BASE}/special-education/deaf-and-hard-of-hearing/guide/">الدليل العملي</a><a href="{BASE}/">الرئيسية</a></nav></div></header>
<main id="main">{body}</main>
<footer><p>محتوى تعليمي غير تشخيصي. راجع المصادر المحلية ومجتمعات الصم في بلدك.</p></footer>
</body></html>"""


def write(rel: str, content: str) -> None:
    target = SITE / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def render_course(data: dict) -> list[str]:
    course = data["course"]
    urls: list[str] = []
    cards = []
    for index, unit in enumerate(course["units"], 1):
        href = f"{BASE}/special-education/deaf-and-hard-of-hearing/course/{unit['slug']}/"
        cards.append(f'<article class="card"><h2>{esc(unit["title"])}</h2><p>{esc(unit["explanation"][0])}</p><a href="{href}">فتح الوحدة {index}</a></article>')
    body = f"""
<h1>{esc(course['title'])}</h1>
<p>{esc(course['duration'])}</p>
<div class="notice"><strong>تنبيه لغوي وثقافي:</strong> {esc(course['variation_notice'])}</div>
<section><h2>لمن هذا المسار؟</h2>{ul(course['audience'])}<p>{esc(course['disclaimer'])}</p></section>
<section><h2>لغة محترمة</h2>{ul(course['respectful_language'])}</section>
<div class="grid">{''.join(cards)}</div>
<section><h2>تقييم تعلم غير تشخيصي</h2><p>{esc(data['assessment']['instructions'])}</p>{''.join(f'<label><input type="checkbox"> {esc(item)}</label>' for item in data['assessment']['items'])}</section>
<section><h2>المصادر</h2>{''.join(f'<p><a href="{esc(s["url"])}">{esc(s["publisher"])} — {esc(s["title"])}</a><br>{esc(s["note"])}</p>' for s in data['sources'])}</section>
"""
    rel = "special-education/deaf-and-hard-of-hearing/index.html"
    canonical = f"{BASE}/special-education/deaf-and-hard-of-hearing/"
    write(rel, page(title=course["title"], description="مسار تمهيدي من خمس وحدات للتواصل المحترم والمتاح مع الصم وضعاف السمع، مع تمارين وتقييم تعليمي ومصادر.", canonical=canonical, body=body, page_type="Course"))
    urls.append(canonical)

    for unit in course["units"]:
        unit_body = f"""
<p><a href="{BASE}/special-education/deaf-and-hard-of-hearing/">العودة إلى المسار</a></p>
<h1>{esc(unit['title'])}</h1>
<section><h2>الأهداف</h2>{ul(unit['objectives'])}</section>
<section><h2>الشرح</h2>{''.join(f'<p>{esc(x)}</p>' for x in unit['explanation'])}</section>
<section><h2>أمثلة</h2>{ul(unit['examples'])}</section>
<section><h2>تمارين تطبيقية</h2>{ul(unit['practice'])}</section>
<section><h2>قائمة تحقق</h2>{''.join(f'<label><input type="checkbox"> {esc(x)}</label>' for x in unit['check'])}</section>
<div class="notice">تحقق من المفردات والإشارات لدى جمعية صم أو مدرب أصم أو جهة وطنية موثوقة في بلدك.</div>
"""
        rel = f"special-education/deaf-and-hard-of-hearing/course/{unit['slug']}/index.html"
        canonical = f"{BASE}/special-education/deaf-and-hard-of-hearing/course/{unit['slug']}/"
        write(rel, page(title=unit["title"], description=unit["explanation"][0], canonical=canonical, body=unit_body, page_type="LearningResource"))
        urls.append(canonical)
    return urls


def render_guide(data: dict) -> list[str]:
    guide = data["guide"]
    scenarios = "".join(f'<article class="card"><h3>{esc(s["title"])}</h3>{ul(s["steps"])}</article>' for s in guide["scenarios"])
    body = f"""
<h1>{esc(guide['title'])}</h1>
<section><h2>متى تستخدم هذا الدليل؟</h2>{ul(guide['when_to_use'])}</section>
<section><h2>ما ينبغي فعله</h2>{ul(guide['do'])}</section>
<section><h2>ما يجب تجنبه</h2>{ul(guide['avoid'])}</section>
<section><h2>مواقف عملية</h2><div class="grid">{scenarios}</div></section>
<section class="safety"><h2>متى تطلب دعمًا متخصصًا؟</h2>{ul(guide['seek_support'])}</section>
<section><h2>روابط مرتبطة</h2><ul><li><a href="{BASE}/special-education/deaf-and-hard-of-hearing/">مسار أساسيات لغة الإشارة العربية</a></li><li><a href="{BASE}/daily-tools/child-listening-prompt/">أداة محادثة استماع مع الطفل</a></li><li><a href="{BASE}/learning-paths/family-listening-5-days/">مسار الاستماع الأسري</a></li></ul></section>
<p class="no-print"><a href="{BASE}/special-education/deaf-and-hard-of-hearing/printable-checklist/">فتح قائمة التحقق القابلة للطباعة</a></p>
"""
    canonical = f"{BASE}/special-education/deaf-and-hard-of-hearing/guide/"
    write("special-education/deaf-and-hard-of-hearing/guide/index.html", page(title=guide["title"], description="خطوات عملية للأسرة والمدرسة والموعد الصحي والطوارئ لتحسين التواصل والإتاحة للصم وضعاف السمع.", canonical=canonical, body=body))

    print_body = f"""
<h1>قائمة تحقق للطباعة: تواصل متاح مع الصم وضعاف السمع</h1>
<p>استخدمها قبل حصة أو اجتماع أو موعد أو نشاط. لا تستبدل التقييم الفردي أو المتطلبات المحلية.</p>
<section>{''.join(f'<label><input type="checkbox"> {esc(x)}</label>' for x in guide['printable_checklist'])}</section>
<section><h2>ملاحظات</h2><p>................................................................................</p><p>................................................................................</p><p>................................................................................</p></section>
<p>تاريخ المراجعة: {esc(data['reviewed_at'])} — الحالة: {esc(data['review_status'])}</p>
"""
    print_canonical = f"{BASE}/special-education/deaf-and-hard-of-hearing/printable-checklist/"
    write("special-education/deaf-and-hard-of-hearing/printable-checklist/index.html", page(title="قائمة تحقق للطباعة للتواصل المتاح", description="قائمة تحقق عملية قابلة للطباعة لتحسين التواصل والإتاحة للصم وضعاف السمع.", canonical=print_canonical, body=print_body, page_type="DigitalDocument"))
    return [canonical, print_canonical]


def main() -> int:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    urls = render_course(data) + render_guide(data)
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    report = {
        "version": 34,
        "center": data["center"],
        "course_units": len(data["course"]["units"]),
        "guides": 1,
        "printables": 1,
        "pages": len(urls),
        "reviewed_at": data["reviewed_at"],
        "review_status": data["review_status"],
        "urls": urls,
    }
    (api / "special-education-v34.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    sitemap = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" + "".join(f"<url><loc>{esc(url)}</loc></url>" for url in urls) + "</urlset>\n"
    write("sitemap-special-education-v34.xml", sitemap)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
