from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "content" / "v34" / "arabic_sign_basics.json"
PUBLISHER = ROOT / "scripts" / "publish_special_education_v34.py"

PROHIBITED = ["الصم والبكم", "تشخيصك", "يعالج نهائيًا", "لغة إشارة عربية موحدة"]
REQUIRED_GUIDE_KEYS = {"when_to_use", "do", "avoid", "scenarios", "seek_support", "printable_checklist"}
REQUIRED_UNIT_KEYS = {"objectives", "explanation", "examples", "practice", "check"}


def validate_source() -> dict:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    course = data["course"]
    assert len(course["units"]) == 5
    assert "تختلف" in course["variation_notice"]
    assert len(course["respectful_language"]) >= 3
    assert REQUIRED_GUIDE_KEYS.issubset(data["guide"])
    assert len(data["guide"]["do"]) >= 7
    assert len(data["guide"]["avoid"]) >= 6
    assert len(data["guide"]["scenarios"]) >= 4
    assert len(data["assessment"]["items"]) >= 6
    assert len(data["sources"]) >= 4
    for unit in course["units"]:
        assert REQUIRED_UNIT_KEYS.issubset(unit)
        assert len(unit["objectives"]) >= 3
        assert len(unit["explanation"]) >= 3
        assert len(unit["practice"]) >= 2
        assert len(unit["check"]) >= 3
    raw = SOURCE.read_text(encoding="utf-8")
    for phrase in PROHIBITED:
        assert phrase not in raw, phrase
    return data


def validate_generated(site: Path) -> None:
    subprocess.run([sys.executable, str(PUBLISHER), str(site)], cwd=ROOT, check=True)
    pages = sorted(site.rglob("index.html"))
    assert len(pages) == 8, [p.relative_to(site).as_posix() for p in pages]
    report = json.loads((site / "api" / "special-education-v34.json").read_text(encoding="utf-8"))
    assert report["course_units"] == 5
    assert report["guides"] == 1
    assert report["printables"] == 1
    assert report["pages"] == 8
    assert report["review_status"] == "needs-local-deaf-community-review"
    sitemap = (site / "sitemap-special-education-v34.xml").read_text(encoding="utf-8")
    assert sitemap.count("<url>") == 8
    for page in pages:
        raw = page.read_text(encoding="utf-8")
        assert 'lang="ar" dir="rtl"' in raw
        assert '<meta name="description"' in raw
        assert '<link rel="canonical"' in raw
        assert 'application/ld+json' in raw
        assert 'twitter:card' in raw
        assert 'href="#main"' in raw
        assert len(raw.split()) > 120, page
        for phrase in PROHIBITED:
            assert phrase not in raw, (page, phrase)
    printable = site / "special-education" / "deaf-and-hard-of-hearing" / "printable-checklist" / "index.html"
    assert "@media print" in printable.read_text(encoding="utf-8")


def main() -> int:
    validate_source()
    with tempfile.TemporaryDirectory() as tmp:
        validate_generated(Path(tmp))
    print("special education v34 validation: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
