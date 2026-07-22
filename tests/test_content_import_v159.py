import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_content_import_v159 import audit


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "data" / "content-entity-contract-v159.json").read_text(encoding="utf-8"))
V2 = list(CONTRACT["v2_required_columns"])
DESCRIPTION = "هذا وصف عربي أصلي وموسع يشرح المفهوم وسياقه والفروق المهمة وحدود الاستخدام ويقدم معلومات عملية دقيقة للقارئ دون تشخيص ذاتي أو وعود علاجية مضللة." * 2


class ContentImportV159Tests(unittest.TestCase):
    def make_root(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "content").mkdir(parents=True)
        (root / "data").mkdir(parents=True)
        (root / "data" / "content-entity-contract-v159.json").write_text(
            json.dumps(CONTRACT, ensure_ascii=False), encoding="utf-8"
        )
        self.addCleanup(temp.cleanup)
        return root

    def write_csv(self, root: Path, name: str, fields: list[str], rows: list[dict[str, str]]):
        path = root / "content" / name
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def valid_v2(self, **overrides):
        row = {
            "schema_version": "2.0.0",
            "entity_id": "term.anxiety",
            "slug": "anxiety",
            "content_type": "term",
            "ar": "القلق",
            "en": "Anxiety",
            "category": "القلق",
            "audience": "general",
            "age_group": "all_ages",
            "risk_level": "moderate",
            "description": DESCRIPTION,
            "keywords": "القلق|أعراض القلق|الصحة النفسية",
            "related": "generalized-anxiety|panic-disorder",
            "source_ids": "who-anxiety-facts",
            "status": "published",
            "review_status": "internally-reviewed",
            "reviewed_at": "2026-07-22",
        }
        row.update(overrides)
        return row

    def test_legacy_template_is_migration_warning_not_error(self):
        root = self.make_root()
        legacy = list(CONTRACT["legacy_v1_columns"])
        self.write_csv(root, "import-template.csv", legacy, [{
            "slug": "example-term",
            "ar": "مثال لمصطلح نفسي",
            "en": "Example Term",
            "category": "تجريبي",
            "description": DESCRIPTION,
            "keywords": "مثال|علم النفس|مصطلحات",
            "related": "related-a|related-b",
            "status": "draft",
            "reviewed_at": "",
        }])
        report = audit(root)
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["legacy_records"], 1)
        self.assertIn("legacy-v1-row", {item["code"] for item in report["warnings"]})

    def test_valid_v2_published_row_passes(self):
        root = self.make_root()
        self.write_csv(root, "import-anxiety-v2.csv", V2, [self.valid_v2()])
        report = audit(root)
        self.assertEqual(report["error_count"], 0)
        self.assertEqual(report["v2_records"], 1)

    def test_high_risk_published_content_requires_sources_and_review(self):
        root = self.make_root()
        self.write_csv(root, "import-treatment-v2.csv", V2, [self.valid_v2(
            entity_id="guide.anxiety-treatment",
            slug="anxiety-treatment",
            content_type="care_guide",
            risk_level="high",
            source_ids="one-source",
            review_status="needs-specialist-review",
        )])
        report = audit(root)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("insufficient-sources", codes)
        self.assertIn("insufficient-review", codes)

    def test_critical_published_content_requires_external_review(self):
        root = self.make_root()
        self.write_csv(root, "import-crisis-v2.csv", V2, [self.valid_v2(
            entity_id="article.urgent-help",
            slug="urgent-help",
            content_type="article",
            risk_level="critical",
            source_ids="who-crisis|official-local-service",
            review_status="internally-reviewed",
        )])
        report = audit(root)
        self.assertIn("critical-review-required", {item["code"] for item in report["errors"]})

    def test_duplicate_slug_and_entity_id_across_batches_fail(self):
        root = self.make_root()
        row = self.valid_v2(status="draft", reviewed_at="")
        self.write_csv(root, "import-a-v2.csv", V2, [row])
        self.write_csv(root, "import-b-v2.csv", V2, [row])
        report = audit(root)
        codes = {item["code"] for item in report["errors"]}
        self.assertIn("duplicate-slug", codes)
        self.assertIn("duplicate-entity-id", codes)

    def test_invalid_header_fails(self):
        root = self.make_root()
        self.write_csv(root, "import-bad.csv", ["slug", "ar"], [{"slug": "bad", "ar": "سيئ"}])
        report = audit(root)
        self.assertIn("invalid-header", {item["code"] for item in report["errors"]})


if __name__ == "__main__":
    unittest.main()
