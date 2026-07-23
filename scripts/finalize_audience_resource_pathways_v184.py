from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
DATA = ROOT / "content" / "v184" / "audience-resource-pathways-ar.json"
RESOURCE_DESCRIPTION = (
    "مكتبة عربية للشرح النفسي المبسط والقاموس العربي–الإنجليزي والإنفوجرافيك "
    "وأوراق العمل القابلة للطباعة، منظمة للشخص والأسرة والمعلم والطالب والمختص."
)


def finalize(site: Path = SITE) -> dict[str, object]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    source_description = data["description"]
    if source_description == RESOURCE_DESCRIPTION:
        raise SystemExit("Resource description must be distinct from the audience portal description")

    target = site / "resources" / "index.html"
    if not target.is_file():
        raise SystemExit(f"Missing resource index: {target}")

    text = target.read_text(encoding="utf-8")
    occurrences = text.count(source_description)
    if occurrences < 4:
        raise SystemExit(
            "Expected the shared description in metadata, social metadata, and JSON-LD before finalization"
        )
    text = text.replace(source_description, RESOURCE_DESCRIPTION)
    if source_description in text:
        raise SystemExit("Shared description remained after resource SEO finalization")
    if text.count(RESOURCE_DESCRIPTION) < 4:
        raise SystemExit("Unique resource description was not applied consistently")
    target.write_text(text, encoding="utf-8")

    report_path = site / "api" / "audience-resource-pathways-v184.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
    report["resources_description_unique"] = True
    report["resources_description"] = RESOURCE_DESCRIPTION
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "page": "resources/index.html",
        "replacements": occurrences,
        "resources_description_unique": True,
    }


if __name__ == "__main__":
    print(json.dumps(finalize(), ensure_ascii=False, indent=2))
