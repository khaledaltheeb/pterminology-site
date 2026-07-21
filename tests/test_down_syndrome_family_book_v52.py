from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK_PATH = ROOT / "content/v18/family-encyclopedia-down-syndrome-ar.json"


def load_book() -> dict:
    payload = json.loads(BOOK_PATH.read_text(encoding="utf-8"))
    return payload["book"]


def flatten_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)
    return ""


def test_book_identity_and_safety_contract() -> None:
    book = load_book()
    assert book["id"] == "family-encyclopedia-down-syndrome-ar"
    assert book["content_type"] == "family-reference-book"
    assert book["language"] == "ar"
    assert book["direction"] == "rtl"
    assert book["review_status"] == "needs-specialist-review"
    assert book["safety_level"] == "sensitive"
    assert book["completion"]["target_substantive_pages"] >= 50
    assert book["completion"]["status"] == "in-progress"


def test_bundle_has_substantive_structure() -> None:
    book = load_book()
    chapters = book["chapters"]
    protocols = book["situational_protocols"]
    sources = book["sources"]

    assert len(chapters) >= 12
    assert len(protocols) >= 6
    assert len(sources) >= 5
    assert len(book["printable_checklists"]) >= 3
    assert len(book["editorial_boundaries"]) >= 5
    assert set(book["evidence_model"]) == {"high", "moderate", "practice", "uncertain"}

    chapter_numbers = [chapter["number"] for chapter in chapters]
    assert chapter_numbers == list(range(1, len(chapters) + 1))

    for chapter in chapters:
        assert chapter["evidence_level"] in book["evidence_model"]
        assert len(chapter["title"]) >= 8
        assert chapter["sections"]
        for section in chapter["sections"]:
            assert len(section["heading"]) >= 5
            assert len(section["paragraphs"]) >= 2
            assert all(len(paragraph) >= 80 for paragraph in section["paragraphs"])


def test_protocols_are_complete_and_actionable() -> None:
    book = load_book()
    required = {
        "id",
        "title",
        "what_i_see",
        "possible_causes",
        "do_now",
        "avoid",
        "monitor",
        "contact_specialist",
        "emergency",
    }
    ids: set[str] = set()
    for protocol in book["situational_protocols"]:
        assert required.issubset(protocol)
        assert protocol["id"] not in ids
        ids.add(protocol["id"])
        assert len(protocol["what_i_see"]) >= 3
        assert len(protocol["possible_causes"]) >= 3
        assert len(protocol["do_now"]) >= 3
        assert len(protocol["avoid"]) >= 3
        assert len(protocol["monitor"]) >= 25
        assert len(protocol["contact_specialist"]) >= 25
        assert len(protocol["emergency"]) >= 25


def test_sources_are_distinct_and_traceable() -> None:
    book = load_book()
    ids = [source["id"] for source in book["sources"]]
    urls = [source["url"] for source in book["sources"]]
    assert len(ids) == len(set(ids))
    assert len(urls) == len(set(urls))
    assert all(url.startswith("https://") for url in urls)
    assert all(source["evidence_type"] for source in book["sources"])
    assert all(source["used_for"] for source in book["sources"])


def test_no_diagnostic_or_prescribing_language() -> None:
    text = flatten_text(load_book())
    banned_patterns = [
        r"شخ[ّ]?ص نفسك",
        r"أنت مصاب حتمًا",
        r"يشفي متلازمة داون",
        r"علاج مضمون",
        r"أوقف الدواء",
        r"غي[ّ]?ر الجرعة",
        r"جرعة مقدارها",
        r"بديل عن الطبيب",
        r"نتيجة مؤكدة 100%",
    ]
    for pattern in banned_patterns:
        assert re.search(pattern, text) is None, pattern

    required_boundaries = [
        "لا يقدّم الكتاب تشخيصًا ذاتيًا",
        "لا يصف أدوية أو جرعات",
        "خدمات الطوارئ المحلية",
        "استبعاد الألم والمرض",
    ]
    for phrase in required_boundaries:
        assert phrase in text


def test_arabic_substantive_word_count_floor() -> None:
    book = load_book()
    text = flatten_text({
        "chapters": book["chapters"],
        "protocols": book["situational_protocols"],
        "checklists": book["printable_checklists"],
    })
    words = re.findall(r"[\u0600-\u06FF]+", text)
    assert len(words) >= 3800


def test_book_does_not_claim_completion_or_specialist_review() -> None:
    book = load_book()
    text = flatten_text(book)
    assert book["completion"]["status"] != "complete"
    assert "تمت مراجعته من اختصاصي" not in text
    assert "كتاب مكتمل من 50 صفحة" not in text
    assert book["next_planned_bundle"]
