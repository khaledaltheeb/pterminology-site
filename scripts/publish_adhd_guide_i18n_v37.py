from __future__ import annotations

import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content/i18n/v37/adhd-family-practical-guide.json"
BASE = "https://khaledaltheeb.github.io/pterminology-site/"
BASE_PATH = "/pterminology-site/"
ENTITY = "adhd-family-practical-guide"
SECTION_KEYS = ["understanding", "what_the_person_may_feel", "do", "avoid", "home_plan", "school_plan", "homework_protocol", "emotion_protocol", "sleep_plan", "medication_awareness", "when_to_seek_help"]
LABELS = {
    "en": {"understanding":"Understanding ADHD without stigma","what_the_person_may_feel":"What the person may feel","do":"What can help","avoid":"What to avoid","home_plan":"Home support plan","school_plan":"School support plan","homework_protocol":"Homework and task-start protocol","emotion_protocol":"Emotional escalation protocol","sleep_plan":"Sleep plan","medication_awareness":"Medication awareness and family boundaries","when_to_seek_help":"When to seek professional help","sources":"Institutional sources","home":"Home","guides":"Care guides","notice":"General educational guide — not a diagnosis","emergency":"When there is immediate risk or acute deterioration"},
    "es": {"understanding":"Comprender el TDAH sin estigma","what_the_person_may_feel":"Lo que puede sentir la persona","do":"Qué puede ayudar","avoid":"Qué conviene evitar","home_plan":"Plan de apoyo en el hogar","school_plan":"Plan de apoyo escolar","homework_protocol":"Protocolo de tareas e inicio","emotion_protocol":"Protocolo de escalada emocional","sleep_plan":"Plan de sueño","medication_awareness":"Información sobre medicación y límites familiares","when_to_seek_help":"Cuándo solicitar ayuda profesional","sources":"Fuentes institucionales","home":"Inicio","guides":"Guías de apoyo","notice":"Guía educativa general — no es un diagnóstico","emergency":"Ante riesgo inmediato o deterioro agudo"}
}

def esc(v: object) -> str:
    return html.escape(str(v), quote=True)

def urls(locale: str, slug: str) -> dict[str, str]:
    ar = BASE + f"care-guides/{ENTITY}/"
    en = BASE + f"en/care-guides/{ENTITY}/"
    es = BASE + f"es/care-guides/{slug if locale == 'es' else 'guia-practica-familiar-tdah'}/"
    return {"ar": ar, "en": en, "es": es, "x-default": ar}

def page(locale: str, guide: dict) -> str:
    lang_urls = urls(locale, guide["slug"])
    canonical = lang_urls[locale]
    label = LABELS[locale]
    alternates = "".join(f'<link rel="alternate" hreflang="{code}" href="{esc(url)}">' for code, url in lang_urls.items())
    switcher = " ".join(f'<a href="{esc(lang_urls[c])}" hreflang="{c}">{name}</a>' for c, name in (("ar","العربية"),("en","English"),("es","Español")))
    sections = "".join(f'<section><h2>{esc(label[k])}</h2><ul>{"".join(f"<li>{esc(x)}</li>" for x in guide[k])}</ul></section>' for k in SECTION_KEYS)
    citations = [s["url"] for s in guide["sources"]]
    schema = json.dumps({"@context":"https://schema.org","@graph":[{"@type":"Article","@id":f"{canonical}#article","headline":guide["title"],"description":guide["summary"],"inLanguage":locale,"mainEntityOfPage":canonical,"citation":citations,"isPartOf":{"@id":f"{BASE}#website"}},{"@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":label["home"],"item":BASE + (f"{locale}/" if locale != "ar" else "")},{"@type":"ListItem","position":2,"name":label["guides"],"item":BASE + f"{locale}/care-guides/"},{"@type":"ListItem","position":3,"name":guide["title"],"item":canonical}]}]}, ensure_ascii=False).replace("</", "<\\/")
    sources = "".join(f'<li><a href="{esc(s["url"])}" rel="noopener noreferrer">{esc(s["publisher"])} — {esc(s["title"])} ({s["year"]})</a></li>' for s in guide["sources"])
    return f'''<!doctype html><html lang="{locale}" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(guide['title'])} | Psychology Terminology</title><meta name="description" content="{esc(guide['summary'])}"><meta name="robots" content="index,follow"><link rel="canonical" href="{esc(canonical)}">{alternates}<link rel="stylesheet" href="{BASE_PATH}assets/css/theme-v10.css"><meta property="og:type" content="article"><meta property="og:locale" content="{'en_US' if locale=='en' else 'es_ES'}"><meta property="og:title" content="{esc(guide['title'])}"><meta property="og:description" content="{esc(guide['summary'])}"><meta property="og:url" content="{esc(canonical)}"><script type="application/ld+json">{schema}</script><style>body{{margin:0;font:18px/1.75 system-ui,Arial,sans-serif;background:#f7fbfb;color:#173f45}}main{{width:min(1000px,92%);margin:auto;padding:2rem 0 4rem}}header,section,aside{{background:white;border:1px solid #c9e9e5;border-radius:20px;padding:1.4rem;margin:1rem 0}}nav{{display:flex;gap:.8rem;flex-wrap:wrap}}a{{color:#086e69}}li{{margin:.5rem 0}}.langs{{margin-top:1rem}}.emergency{{border-inline-start:6px solid #c7476e;background:#fff0f3}}@media(max-width:640px){{body{{font-size:16px}}nav{{display:grid}}}}</style></head><body><main><header><nav aria-label="{esc(label['guides'])}"><a href="{BASE_PATH}{locale + '/' if locale != 'ar' else ''}">{esc(label['home'])}</a><a href="{BASE_PATH}{locale}/care-guides/">{esc(label['guides'])}</a></nav><div class="langs" aria-label="Language">{switcher}</div><p>{esc(label['notice'])}</p><h1>{esc(guide['title'])}</h1><p>{esc(guide['summary'])}</p></header>{sections}<aside class="emergency"><strong>{esc(label['emergency'])}:</strong> {esc(guide['emergency_note'])}</aside><section><h2>{esc(label['sources'])}</h2><ul>{sources}</ul><p>{esc(guide['disclaimer'])}</p></section></main></body></html>'''

def patch_arabic_hreflang() -> None:
    path = SITE / "care-guides" / ENTITY / "index.html"
    if not path.exists():
        raise SystemExit(f"Missing Arabic source page: {path}")
    text = path.read_text(encoding="utf-8")
    ar_urls = urls("ar", ENTITY)
    marker = '<link rel="alternate" hreflang="x-default"'
    insertion = f'<link rel="alternate" hreflang="en" href="{ar_urls["en"]}"><link rel="alternate" hreflang="es" href="{ar_urls["es"]}">'
    if 'hreflang="en"' not in text:
        text = text.replace(marker, insertion + marker)
    path.write_text(text, encoding="utf-8")

def write_sitemap(locales: dict) -> None:
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    xhtml = "http://www.w3.org/1999/xhtml"
    ET.register_namespace("xhtml", xhtml)
    root = ET.Element("urlset", xmlns=ns)
    all_urls = urls("en", locales["en"]["slug"])
    for locale in ("ar", "en", "es"):
        node = ET.SubElement(root, "url")
        ET.SubElement(node, "loc").text = all_urls[locale]
        for code, href in all_urls.items():
            ET.SubElement(node, f"{{{xhtml}}}link", rel="alternate", hreflang=code, href=href)
    ET.ElementTree(root).write(SITE / "sitemap-adhd-guide-i18n.xml", encoding="utf-8", xml_declaration=True)

def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    locales = data["locales"]
    for locale in ("en", "es"):
        if locales[locale]["status"] not in {"linguistically-reviewed", "scientifically-reviewed", "published", "translated"}:
            raise SystemExit(f"Incomplete locale: {locale}")
        out = SITE / locale / "care-guides" / locales[locale]["slug"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(locale, locales[locale]), encoding="utf-8")
    patch_arabic_hreflang()
    write_sitemap(locales)
    report = {"entity_id": data["entity_id"], "locales": ["ar", "en", "es"], "translated_entities": 1, "generated_pages": 2, "status": {k: locales[k]["status"] for k in ("en", "es")}}
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "adhd-guide-i18n-v37.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
