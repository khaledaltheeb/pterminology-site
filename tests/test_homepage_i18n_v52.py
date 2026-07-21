import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "content/i18n/v52/homepage.json"


def test_homepage_i18n_contract_and_output():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert data["entity_id"] == "page.home"
    assert data["source_locale"] == "ar"
    allowed = set(data["allowed_statuses"])
    assert allowed == {
        "draft",
        "translated",
        "linguistically-reviewed",
        "scientifically-reviewed",
        "published",
    }
    required = set(data["required_fields"])
    for locale in ("en", "es"):
        page = data["locales"][locale]
        assert page["status"] == "linguistically-reviewed"
        assert page["status"] in allowed
        assert required.issubset(page)
        assert all(page[field] for field in required)
        assert page["review"]["type"] == "linguistic"
        assert page["review"]["reviewed_at"] == data["reviewed_at"]
        assert page["review"]["scientific_review"] == "pending"
        assert {
            "clarity",
            "terminology",
            "tone",
            "safety wording",
            "field completeness",
        }.issubset(page["review"]["review_scope"])
        assert len(page["sections"]["cards"]) == 6
        assert len(page["sections"]["quality"]) == 4

    subprocess.run(["python3", "scripts/publish_homepage_i18n_v52.py"], cwd=ROOT, check=True)
    for locale in ("en", "es"):
        text = (ROOT / locale / "index.html").read_text(encoding="utf-8")
        assert f'<html lang="{locale}" dir="ltr">' in text
        assert f'<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site/{locale}/">' in text
        for code in ("ar", "en", "es", "x-default"):
            assert f'hreflang="{code}"' in text
        assert "self-diagnosis" in text or "autodiagnóstico" in text
        assert "../" in text
