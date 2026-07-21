from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content/i18n/v37/adhd-family-practical-guide.json"
PUBLISHER = ROOT / "scripts/publish_adhd_guide_i18n_v37.py"
AR_SOURCE = ROOT / "content/v18/care-guides-adhd-ar.json"
REQUIRED = {"slug", "title", "audience", "search_intent", "summary", "understanding", "what_the_person_may_feel", "do", "avoid", "home_plan", "school_plan", "homework_protocol", "emotion_protocol", "sleep_plan", "medication_awareness", "when_to_seek_help", "emergency_note", "disclaimer", "sources", "status"}
SECTIONS = ["understanding", "what_the_person_may_feel", "do", "avoid", "home_plan", "school_plan", "homework_protocol", "emotion_protocol", "sleep_plan", "medication_awareness", "when_to_seek_help"]

def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    assert payload["entity_id"] == "guide.adhd.family-practical"
    assert payload["source_locale"] == "ar"
    source = json.loads(AR_SOURCE.read_text(encoding="utf-8"))["guides"][0]
    locales = payload["locales"]
    assert set(locales) == {"en", "es"}
    for locale, guide in locales.items():
        assert REQUIRED <= set(guide), (locale, REQUIRED - set(guide))
        assert guide["status"] in {"translated", "linguistically-reviewed", "scientifically-reviewed", "published"}
        assert len(guide["title"]) >= 35 and len(guide["summary"]) >= 140
        assert len(guide["audience"]) == len(source["audience"])
        assert len(guide["sources"]) == len(source["sources"]) >= 4
        assert [s["url"] for s in guide["sources"]] == [s["url"] for s in source["sources"]]
        for key in SECTIONS:
            assert len(guide[key]) >= 5, (locale, key)
            assert all(len(item.strip()) >= 18 for item in guide[key])
        joined = " ".join(str(v) for v in guide.values()).lower()
        assert "diagnose yourself" not in joined and "autodiagnóstico" not in joined
        assert "change the dose" not in joined and "cambiar la dosis por cuenta propia" not in joined
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp)
        ar = site / "care-guides/adhd-family-practical-guide/index.html"
        ar.parent.mkdir(parents=True)
        ar.write_text('<html lang="ar" dir="rtl"><head><link rel="alternate" hreflang="ar" href="x"><link rel="alternate" hreflang="x-default" href="x"></head><body></body></html>', encoding="utf-8")
        (site / "sitemap.xml").write_text('<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>', encoding="utf-8")
        subprocess.run([sys.executable, str(PUBLISHER), str(site)], check=True, cwd=ROOT)
        en = (site / "en/care-guides/adhd-family-practical-guide/index.html").read_text(encoding="utf-8")
        es = (site / "es/care-guides/guia-practica-familiar-tdah/index.html").read_text(encoding="utf-8")
        patched_ar = ar.read_text(encoding="utf-8")
        for text, locale in ((en, "en"), (es, "es")):
            assert f'<html lang="{locale}" dir="ltr">' in text
            assert text.count('rel="canonical"') == 1
            for code in ("ar", "en", "es", "x-default"):
                assert f'hreflang="{code}"' in text
            assert 'application/ld+json' in text and 'BreadcrumbList' in text and 'Article' in text
            assert 'index,follow' in text
        assert 'dir="rtl"' in patched_ar and 'hreflang="en"' in patched_ar and 'hreflang="es"' in patched_ar
        sitemap = (site / "sitemap-adhd-guide-i18n.xml").read_text(encoding="utf-8")
        assert sitemap.count("<url>") == 3
        assert "xhtml:link" in sitemap
        report = json.loads((site / "api/adhd-guide-i18n-v37.json").read_text(encoding="utf-8"))
        assert report["translated_entities"] == 1 and report["generated_pages"] == 2
    print("ADHD guide i18n v37 validation passed")

if __name__ == "__main__":
    main()
