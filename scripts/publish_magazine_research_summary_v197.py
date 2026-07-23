from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v197" / "magazine-phq-gad-instruction-emphasis-ar.json"
BASE_URL = "https://khaledaltheeb.github.io/pterminology-site"
BASE_PATH = "/pterminology-site/"
SITEMAP_NAME = "sitemap-magazine-research.xml"
ARTICLE_START = "<!-- magazine-research-summary-v197:start -->"
ARTICLE_END = "<!-- magazine-research-summary-v197:end -->"
CARD_START = "<!-- magazine-research-card-v197:start -->"
CARD_END = "<!-- magazine-research-card-v197:end -->"


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


class VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "nav", "footer"}:
            self.hidden += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)

    def word_count(self) -> int:
        text = re.sub(r"\s+", " ", " ".join(self.parts))
        return len(re.findall(r"[\w\u0600-\u06ff]+", text, flags=re.UNICODE))


def visible_word_count(text: str) -> int:
    parser = VisibleText()
    parser.feed(text)
    return parser.word_count()


def load_content() -> dict[str, Any]:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    required = {
        "id", "version", "status", "publication_status", "risk_level",
        "reviewed_at", "created_at", "slug", "title", "seo_title",
        "description", "summary", "journal", "original_publication_date",
        "doi", "pmid", "trial_registration", "study_type", "original_authors",
        "direct_answer", "study_snapshot", "key_numbers", "sections",
        "editorial_takeaways", "safety_notice", "funding", "conflicts",
        "sources", "internal_links",
    }
    missing = required - set(data)
    if missing:
        raise SystemExit(f"Missing magazine summary fields: {sorted(missing)}")
    if data["version"] != 197:
        raise SystemExit("Magazine summary version must remain 197")
    if data["status"] != "internally-reviewed":
        raise SystemExit("Magazine summary must remain internally-reviewed")
    if data["publication_status"] != "built-not-published":
        raise SystemExit("Magazine summary must not claim publication")
    if data["risk_level"] != "moderate":
        raise SystemExit("Research summary must retain moderate-risk review status")
    if not 110 <= len(data["description"]) <= 180:
        raise SystemExit("Meta description must remain between 110 and 180 characters")
    if len(data["sections"]) < 9:
        raise SystemExit("Research summary requires at least nine substantive sections")
    if len(data["sources"]) < 4:
        raise SystemExit("Research summary requires primary, index, commentary and registry sources")
    if len(data["internal_links"]) < 5:
        raise SystemExit("Research summary requires five contextual internal links")

    source_ids = [source["id"] for source in data["sources"]]
    source_urls = [source["url"] for source in data["sources"]]
    if len(source_ids) != len(set(source_ids)) or len(source_urls) != len(set(source_urls)):
        raise SystemExit("Source IDs and URLs must be unique")
    if any(not url.startswith("https://") for url in source_urls):
        raise SystemExit("All sources must use HTTPS")
    if sum(source.get("type") == "primary-study" for source in data["sources"]) != 1:
        raise SystemExit("Exactly one primary study source is required")
    if data["doi"] not in json.dumps(data, ensure_ascii=False):
        raise SystemExit("DOI must be retained in the content record")

    serialized = json.dumps(data, ensure_ascii=False)
    required_phrases = [
        "لم يكن تحسنًا علاجيًا", "لا تقدم تشخيصًا", "لا تغيّر دواءً",
        "تعارض المصالح", "التسجيل المسبق",
    ]
    for phrase in required_phrases:
        if phrase not in serialized:
            raise SystemExit(f"Missing safety or transparency phrase: {phrase}")
    prohibited = [
        "يثبت أن المقياس غير صالح", "يعالج الاكتئاب", "يشخص القلق نهائيًا",
        "توصية طبية شخصية", "مراجعة اختصاصية مكتملة", "منشور حيًا",
    ]
    for phrase in prohibited:
        if phrase in serialized:
            raise SystemExit(f"Prohibited claim detected: {phrase}")
    return data


def article_schema(data: dict[str, Any]) -> str:
    canonical = f'{BASE_URL}/magazine/{data["slug"]}/'
    citations = [source["url"] for source in data["sources"]]
    graph = [
        {
            "@type": "Organization",
            "@id": f"{BASE_URL}/#organization",
            "name": "المنصة الشاملة للصحة النفسية وذوي الاحتياجات الخاصة",
            "alternateName": "مصطلحات علم النفس",
            "url": f"{BASE_URL}/",
        },
        {
            "@type": "Article",
            "@id": f"{canonical}#article",
            "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
            "headline": data["title"],
            "description": data["description"],
            "inLanguage": "ar",
            "dateCreated": data["created_at"],
            "dateModified": data["reviewed_at"],
            "articleSection": "ملخصات الأبحاث والمقاييس النفسية",
            "author": {
                "@type": "Organization",
                "name": "هيئة تحرير مجلة الصحة النفسية والبحث العلمي",
                "url": f"{BASE_URL}/magazine/",
            },
            "publisher": {"@id": f"{BASE_URL}/#organization"},
            "citation": citations,
            "isBasedOn": citations[0],
            "about": [
                {"@type": "Thing", "name": "Patient Health Questionnaire-9 (PHQ-9)"},
                {"@type": "Thing", "name": "Generalized Anxiety Disorder-7 (GAD-7)"},
                {"@type": "Thing", "name": "قياس أعراض الاكتئاب والقلق"},
            ],
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "الرئيسية", "item": f"{BASE_URL}/"},
                {"@type": "ListItem", "position": 2, "name": "المجلة", "item": f"{BASE_URL}/magazine/"},
                {"@type": "ListItem", "position": 3, "name": data["title"], "item": canonical},
            ],
        },
    ]
    return json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/")


def render_snapshot(data: dict[str, Any]) -> str:
    labels = {
        "population": "المشاركون", "recruitment": "الاستقطاب", "groups": "التوزيع",
        "mean_age": "العمر والجنس", "procedure": "الإجراء",
        "primary_outcomes": "النتائج الأساسية", "secondary_outcomes": "النتائج الثانوية",
    }
    rows = "".join(
        f'<div class="fact"><dt>{esc(labels[key])}</dt><dd>{esc(value)}</dd></div>'
        for key, value in data["study_snapshot"].items()
    )
    return f'<dl class="facts">{rows}</dl>'


def render_numbers(data: dict[str, Any]) -> str:
    cards = "".join(
        f'<article class="number-card"><h3>{esc(item["label"])}</h3><strong>{esc(item["value"])}</strong><p>{esc(item["detail"])}</p></article>'
        for item in data["key_numbers"]
    )
    return f'<div class="number-grid">{cards}</div>'


def render_sections(data: dict[str, Any]) -> str:
    return "".join(
        f'<section class="content-card"><h2>{esc(section["heading"])}</h2>'
        + "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
        + "</section>"
        for section in data["sections"]
    )


def render_sources(data: dict[str, Any]) -> str:
    items = []
    for source in data["sources"]:
        extra = []
        if source.get("doi"):
            extra.append(f'DOI: {esc(source["doi"])}')
        if source.get("registration"):
            extra.append(f'التسجيل: {esc(source["registration"])}')
        details = " — " + "؛ ".join(extra) if extra else ""
        items.append(
            f'<li><a href="{esc(source["url"])}" rel="noopener noreferrer">{esc(source["title"])}</a>'
            f' — {esc(source["publisher"])}{details}. <small>تم التحقق: {esc(source["accessed_at"])}</small></li>'
        )
    return "<ol>" + "".join(items) + "</ol>"


def render_internal_links(data: dict[str, Any]) -> str:
    return "<ul>" + "".join(
        f'<li><a href="{esc(item["href"])}">{esc(item["label"])}</a></li>'
        for item in data["internal_links"]
    ) + "</ul>"


def render_article(data: dict[str, Any]) -> str:
    canonical = f'{BASE_URL}/magazine/{data["slug"]}/'
    takeaways = "".join(f"<li>{esc(item)}</li>" for item in data["editorial_takeaways"])
    author_names = "، ".join(data["original_authors"])
    schema = article_schema(data)
    return f'''<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(data["seo_title"])}</title>
<meta name="description" content="{esc(data["description"])}">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<link rel="canonical" href="{canonical}">
<link rel="manifest" href="{BASE_PATH}manifest.webmanifest">
<meta name="color-scheme" content="light">
<meta name="theme-color" content="#f7fbfa">
<meta property="og:type" content="article">
<meta property="og:locale" content="ar_AR">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{esc(data["title"])}">
<meta property="og:description" content="{esc(data["description"])}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(data["title"])}">
<meta name="twitter:description" content="{esc(data["description"])}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#173f45;--muted:#4b686b;--surface:#fff;--page:#f7fbfa;--line:#b7d9d4;--accent:#075d64;--accent-soft:#e5f6f3;--warning:#6a3d00;--warning-bg:#fff4db;--danger:#7b2338;--danger-bg:#fff0f3;--shadow:0 14px 40px rgba(23,63,69,.09)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--page);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.95}}
a{{color:var(--accent);font-weight:700}}a:focus-visible{{outline:3px solid #7a4b00;outline-offset:4px}}
.skip{{position:absolute;right:-9999px;top:8px;background:#fff;color:var(--ink);padding:10px 14px;border:2px solid var(--accent);border-radius:10px;z-index:100}}.skip:focus{{right:8px}}
.wrap{{width:min(1060px,92%);margin:auto}}nav{{padding:18px 0}}main{{padding-bottom:60px}}
.hero,.content-card,.evidence,.notice,.sources,.related{{background:var(--surface);border:1px solid var(--line);border-radius:20px;padding:clamp(20px,4vw,34px);margin:18px 0;box-shadow:var(--shadow)}}
.kicker{{font-weight:900;color:var(--danger)}}h1{{font-size:clamp(2rem,5vw,3.6rem);line-height:1.25;margin:.25em 0}}h2{{font-size:clamp(1.45rem,3vw,2.15rem);line-height:1.4}}h3{{line-height:1.5}}
.lead{{font-size:1.16rem;color:var(--muted)}}.meta{{display:flex;gap:10px;flex-wrap:wrap;padding:0;list-style:none}}.meta li{{background:var(--accent-soft);border:1px solid var(--line);border-radius:999px;padding:7px 12px}}
.direct{{border-inline-start:6px solid var(--accent);background:var(--accent-soft)}}.warning{{border-inline-start:6px solid var(--warning);background:var(--warning-bg)}}.safety{{border-inline-start:6px solid var(--danger);background:var(--danger-bg)}}
.facts{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}.fact{{background:#f9fcfb;border:1px solid var(--line);border-radius:14px;padding:14px}}dt{{font-weight:900;margin-bottom:6px}}dd{{margin:0;color:var(--muted)}}
.number-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}.number-card{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px}}.number-card strong{{display:block;font-size:1.55rem;color:var(--danger);margin:.4rem 0}}.number-card p{{color:var(--muted)}}
.content-card p{{max-width:78ch}}small{{color:var(--muted)}}footer{{padding:28px 0 46px;color:var(--muted)}}
@media(max-width:760px){{.facts,.number-grid{{grid-template-columns:1fr}}}}
@media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}}}
@media print{{.skip,nav{{display:none}}body{{background:#fff}}.wrap{{width:100%}}.hero,.content-card,.evidence,.notice,.sources,.related{{box-shadow:none;break-inside:avoid;border-color:#777}}a{{color:#000;text-decoration:underline}}}}
</style>
</head>
<body>
<a class="skip" href="#main">انتقل إلى المحتوى الرئيسي</a>
<div class="wrap">
<nav aria-label="مسار الصفحة"><a href="{BASE_PATH}">الرئيسية</a> ← <a href="{BASE_PATH}magazine/">المجلة</a> ← ملخص دراسة</nav>
<main id="main">
<article>
<header class="hero">
<p class="kicker">ملخص بحثي نقدي · تجربة عشوائية · حالة التحرير: مبني وغير منشور</p>
<h1>{esc(data["title"])}</h1>
<p class="lead">{esc(data["summary"])}</p>
<ul class="meta">
<li>المجلة: {esc(data["journal"])}</li>
<li>نشر المصدر: <time datetime="{esc(data["original_publication_date"])}">{esc(data["original_publication_date"])}</time></li>
<li>DOI: {esc(data["doi"])}</li>
<li>التسجيل: {esc(data["trial_registration"])}</li>
</ul>
<p><strong>مؤلفو الدراسة الأصلية:</strong> {esc(author_names)}.</p>
</header>
<section class="notice direct" aria-labelledby="direct-answer"><h2 id="direct-answer">الخلاصة المباشرة</h2><p>{esc(data["direct_answer"])}</p></section>
<section class="evidence" aria-labelledby="study-snapshot"><h2 id="study-snapshot">بطاقة الدراسة</h2><p><strong>نوع الدراسة:</strong> {esc(data["study_type"])}</p>{render_snapshot(data)}</section>
<section class="evidence" aria-labelledby="key-results"><h2 id="key-results">الأرقام الأساسية</h2>{render_numbers(data)}</section>
{render_sections(data)}
<section class="notice warning" aria-labelledby="editorial-takeaways"><h2 id="editorial-takeaways">ما الذي يجب أن يتغير في إدارة المقاييس؟</h2><ul>{takeaways}</ul></section>
<section class="notice safety" aria-labelledby="safety-notice"><h2 id="safety-notice">حدود السلامة</h2><p>{esc(data["safety_notice"])}</p></section>
<section class="sources" aria-labelledby="sources"><h2 id="sources">المصادر الأولية وسجل التحقق</h2>{render_sources(data)}</section>
<section class="content-card" aria-labelledby="disclosures"><h2 id="disclosures">التمويل والإفصاحات</h2><p><strong>التمويل:</strong> {esc(data["funding"])}</p><p><strong>تعارض المصالح:</strong> {esc(data["conflicts"])}</p></section>
<section class="related" aria-labelledby="related"><h2 id="related">مسارات مرتبطة داخل المنصة</h2>{render_internal_links(data)}</section>
<section class="notice"><h2>حالة الصفحة</h2><p>أُعدت هذه النسخة في {esc(data["reviewed_at"])} بمراجعة داخلية، وحالتها التقنية <code>{esc(data["publication_status"])}</code>. لا توجد مراجعة اختصاصية خارجية معلنة، ولا تعد الصفحة منشورة حيًا قبل نجاح بوابة النشر وتطابق SHA والملف الحي.</p></section>
</article>
</main>
<footer><p>© المنصة الشاملة للصحة النفسية وذوي الاحتياجات الخاصة — الاسم المؤسس: مصطلحات علم النفس.</p></footer>
</div>
</body>
</html>'''


def index_card(data: dict[str, Any]) -> str:
    return f'''{CARD_START}
<section class="institutional-card" aria-labelledby="research-summary-v197">
<h2 id="research-summary-v197">أول ملخص بحثي قيد المراجعة</h2>
<article>
<h3>{esc(data["title"])}</h3>
<p>{esc(data["summary"])}</p>
<p><strong>نوع الدراسة:</strong> {esc(data["study_type"])}. <strong>المصدر:</strong> {esc(data["journal"])}، {esc(data["original_publication_date"])}.</p>
<p><a href="{BASE_PATH}magazine/{esc(data["slug"])}/">قراءة الملخص النقدي الكامل</a></p>
<p><small>الحالة: مبني وغير منشور حيًا؛ لا توجد مراجعة اختصاصية خارجية معلنة.</small></p>
</article>
</section>
{CARD_END}'''


def update_magazine_index(site: Path, data: dict[str, Any]) -> bool:
    path = site / "magazine" / "index.html"
    if not path.is_file():
        raise SystemExit("Magazine index is missing; run institutional foundation publisher first")
    text = path.read_text(encoding="utf-8")
    card = index_card(data)
    pattern = re.compile(re.escape(CARD_START) + r".*?" + re.escape(CARD_END), re.S)
    if pattern.search(text):
        updated = pattern.sub(card, text, count=1)
        changed = updated != text
        text = updated
    else:
        marker = '<section class="notice">'
        if marker in text:
            text = text.replace(marker, card + "\n" + marker, 1)
        elif "</main>" in text:
            text = text.replace("</main>", card + "\n</main>", 1)
        else:
            raise SystemExit("Magazine index has no safe insertion marker")
        changed = True

    old_status = "لم تُنشر في هذه الحزمة ملخصات دراسات منفردة بعد. تبدأ المجلة بالمنهج والعقد التحريري، ثم تدخل كل دراسة في Queue مستقلة ولا تظهر كمنشورة قبل فحص المصدر والبوابات والنسخة الحية."
    new_status = "أُعد أول ملخص بحثي في هذه الحزمة للمراجعة الداخلية، لكنه لا يعد منشورًا حيًا قبل نجاح فحص المصدر والبوابات وGitHub Pages وتطابق SHA والملف الحي."
    text = text.replace(old_status, new_status)
    if text.count(f'/magazine/{data["slug"]}/') != 1:
        raise SystemExit("Magazine article link must appear exactly once in magazine index")
    path.write_text(text, encoding="utf-8")
    return changed


def write_sitemap(site: Path, data: dict[str, Any]) -> int:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)
    root = ET.Element(f"{{{namespace}}}urlset")
    url = ET.SubElement(root, f"{{{namespace}}}url")
    ET.SubElement(url, f"{{{namespace}}}loc").text = f'{BASE_URL}/magazine/{data["slug"]}/'
    ET.SubElement(url, f"{{{namespace}}}lastmod").text = data["reviewed_at"]
    ET.SubElement(url, f"{{{namespace}}}changefreq").text = "monthly"
    ET.ElementTree(root).write(site / SITEMAP_NAME, encoding="utf-8", xml_declaration=True)
    return 1


def update_foundation_report(site: Path) -> None:
    path = site / "api" / "institutional-foundation-v192.json"
    if not path.is_file():
        return
    report = json.loads(path.read_text(encoding="utf-8"))
    report["prepared_research_summaries"] = 1
    report["published_research_summaries"] = 0
    report["magazine_research_summary_version"] = 197
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def publish(site: Path) -> dict[str, Any]:
    if not site.is_dir():
        raise SystemExit(f"Missing site output: {site}")
    data = load_content()
    target = site / "magazine" / data["slug"] / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    text = render_article(data)
    words = visible_word_count(text)
    if words < 1450:
        raise SystemExit(f"Research summary is too short: {words} visible words")
    target.write_text(text, encoding="utf-8")
    index_changed = update_magazine_index(site, data)
    sitemap_urls = write_sitemap(site, data)
    update_foundation_report(site)
    report = {
        "version": 197,
        "status": "built-not-published",
        "review_status": data["status"],
        "risk_level": data["risk_level"],
        "page": f'/magazine/{data["slug"]}/',
        "visible_words": words,
        "source_count": len(data["sources"]),
        "primary_source_count": sum(source["type"] == "primary-study" for source in data["sources"]),
        "doi": data["doi"],
        "pmid": data["pmid"],
        "trial_registration": data["trial_registration"],
        "magazine_index_updated": index_changed,
        "sitemap": f"/{SITEMAP_NAME}",
        "sitemap_urls": sitemap_urls,
        "published_research_summaries": 0,
        "prepared_research_summaries": 1,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "magazine-research-summary-v197.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    publish(args.site.resolve())


if __name__ == "__main__":
    main()
