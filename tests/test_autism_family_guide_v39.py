from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content/v18/care-guides-autism-ar.json"
PUBLISHER = ROOT / "scripts/publish_care_guides_v21.py"


def load_guide() -> dict:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    assert payload["version"] == 39
    assert payload["language"] == "ar"
    assert len(payload["guides"]) == 1
    return payload["guides"][0]


def test_autism_guide_identity_and_depth() -> None:
    guide = load_guide()
    assert guide["id"] == "guide.autism.family-practical"
    assert guide["slug"] == "autism-family-practical-guide"
    assert guide["review_status"] == "needs-review"
    required = {
        "understanding", "what_the_person_may_feel", "strengths_and_differences",
        "communication_plan", "sensory_plan", "do", "avoid", "home_plan",
        "school_plan", "transition_protocol", "meltdown_protocol",
        "wandering_protocol", "sleep_plan", "food_plan",
        "medication_awareness", "when_to_seek_help", "caregiver_plan",
    }
    assert required.issubset(guide)
    assert sum(len(guide[key]) for key in required) >= 80
    assert len(guide["sources"]) >= 4


def test_protocols_cover_action_avoid_escalation_and_emergency() -> None:
    guide = load_guide()
    for key in ("transition_protocol", "meltdown_protocol", "wandering_protocol"):
        text = " ".join(guide[key])
        assert "ماذا أفعل" in text
        assert "أتجنب" in text
        assert "مختص" in text
        assert "طارئة" in text


def test_safety_and_non_diagnostic_language() -> None:
    guide = load_guide()
    text = json.dumps(guide, ensure_ascii=False)
    assert "التشخيص مهني" in text
    assert "لا توقف الدواء" in text
    assert "خدمات الطوارئ المحلية" in text
    assert "يشفي التوحد" in text
    assert "راجع الألم" in text


def test_publisher_integrates_existing_library() -> None:
    text = PUBLISHER.read_text(encoding="utf-8")
    assert "content/v18/care-guides-autism-ar.json" in text
    assert "Expected 8 validated guides" in text
    assert "autism-family-practical-guide" in text
    assert '"transition_protocol"' in text
    assert '"meltdown_protocol"' in text
    assert '"wandering_protocol"' in text
    assert "@media print" in text
