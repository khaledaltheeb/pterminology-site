from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content/v18/care-guides-adhd-ar.json"
WORD_RE = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)

REQUIRED_SECTIONS = {
    "understanding",
    "what_the_person_may_feel",
    "do",
    "avoid",
    "home_plan",
    "school_plan",
    "homework_protocol",
    "emotion_protocol",
    "sleep_plan",
    "medication_awareness",
    "when_to_seek_help",
    "caregiver_plan",
    "observe",
    "conversation_steps",
    "plan",
    "warning_signs",
}

TRUSTED_SOURCE_HOSTS = {
    "www.nice.org.uk",
    "www.cdc.gov",
    "publications.aap.org",
    "icd.who.int",
}

PROHIBITED_PATTERNS = (
    r"يشخ[ّ]?صك",
    r"تشخيص نهائي",
    r"شفاء مضمون",
    r"يعالج نهائي[ًاا]",
    r"أوقف الدواء",
    r"غي[ّ]?ر الجرعة بنفسك",
)


def load_guide() -> dict:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert data["language"] == "ar"
    assert len(data["guides"]) == 1
    return data["guides"][0]


def substantive_word_count(guide: dict) -> int:
    parts: list[str] = [guide["title"], guide["summary"], guide["emergency_note"]]
    for key in REQUIRED_SECTIONS:
        parts.extend(guide[key])
    return len(WORD_RE.findall(" ".join(parts)))


def test_complete_high_value_structure() -> None:
    guide = load_guide()
    assert guide["slug"] == "adhd-family-practical-guide"
    assert REQUIRED_SECTIONS.issubset(guide)
    assert all(len(guide[key]) >= 8 for key in REQUIRED_SECTIONS)
    assert substantive_word_count(guide) >= 2200
    assert len(guide["audience"]) >= 4
    assert len(guide["search_intent"]) >= 3


def test_medical_safety_and_non_diagnostic_boundaries() -> None:
    guide = load_guide()
    rendered = json.dumps(guide, ensure_ascii=False)
    for pattern in PROHIBITED_PATTERNS:
        assert re.search(pattern, rendered, re.IGNORECASE) is None, pattern
    assert "لا يُشخّص ADHD من سلوك واحد أو اختبار إلكتروني" in rendered
    assert "لا توجد جرعة عامة مناسبة للجميع" in rendered
    assert "خدمات الطوارئ المحلية" in guide["emergency_note"]
    assert any("إيذاء النفس" in item for item in guide["warning_signs"])


def test_sources_are_primary_institutional_and_unique() -> None:
    guide = load_guide()
    sources = guide["sources"]
    assert len(sources) >= 6
    urls = [source["url"] for source in sources]
    assert len(urls) == len(set(urls))
    for source in sources:
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https"
        assert parsed.netloc in TRUSTED_SOURCE_HOSTS
        assert source["publisher"].strip()
        assert source["title"].strip()
        assert 2018 <= int(source["year"]) <= 2026


def test_sections_are_not_repetitive() -> None:
    guide = load_guide()
    normalized: list[str] = []
    for key in REQUIRED_SECTIONS:
        for item in guide[key]:
            value = re.sub(r"\s+", " ", item).strip().casefold()
            assert len(WORD_RE.findall(value)) >= 7, (key, item)
            normalized.append(value)
    assert len(normalized) == len(set(normalized))
