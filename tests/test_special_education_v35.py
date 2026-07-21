import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "v35" / "executable-instructions-adhd-learning-difficulties.json"


def load_content() -> dict:
    with CONTENT.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_required_metadata_and_non_diagnostic_limits() -> None:
    data = load_content()
    required = {
        "id",
        "slug",
        "content_type",
        "title_ar",
        "summary",
        "audiences",
        "age_groups",
        "reviewed_at",
        "review_status",
        "safety_level",
        "schema_types",
        "professional_limits",
    }
    assert required.issubset(data)
    assert data["content_type"] == "course"
    assert data["review_status"] == "needs-review"
    assert "غير تشخيصية" in data["professional_limits"]
    assert "خطة تعليمية فردية" in data["professional_limits"]


def test_course_is_complete_and_practical() -> None:
    data = load_content()
    assert len(data["learning_outcomes"]) >= 5
    assert len(data["core_principles"]) >= 4
    assert len(data["units"]) == 3
    for unit in data["units"]:
        assert len(unit["objectives"]) >= 3
        assert len(unit["explanation"]) >= 3
        assert len(unit["practice"]) >= 3
        assert len(unit["non_diagnostic_check"]) >= 4
    assert len(data["scenario_assessment"]) >= 3
    assert len(data["printable"]["fields"]) >= 8


def test_sources_and_internal_links_are_present() -> None:
    data = load_content()
    assert len(data["sources"]) >= 4
    assert {source["organization"] for source in data["sources"]} >= {
        "CDC",
        "UNICEF",
        "UNESCO",
    }
    for source in data["sources"]:
        assert source["url"].startswith("https://")
        assert source["accessed_at"] == "2026-07-21"
    assert len(data["internal_links"]) >= 3
    for link in data["internal_links"]:
        assert link["target"].startswith("/")


def test_language_avoids_personality_judgments() -> None:
    text = json.dumps(load_content(), ensure_ascii=False)
    prohibited = [
        "الطالب كسول",
        "الطالب عنيد",
        "سيئ التربية",
        "تشخيص نهائي",
        "استغن عن المختص",
    ]
    for phrase in prohibited:
        assert phrase not in text


def test_escalation_and_medical_rule_out_are_explicit() -> None:
    data = load_content()
    text = json.dumps(data, ensure_ascii=False)
    assert "الألم" in text
    assert "المرض" in text
    assert "التنمر" in text
    assert "إيذاء للنفس أو الآخرين" in text
    assert "مساعدة فورية" in text
