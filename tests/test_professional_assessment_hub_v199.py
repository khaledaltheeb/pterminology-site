from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_professional_assessment_hub_v199.py"

spec = importlib.util.spec_from_file_location("validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


class ProfessionalAssessmentHubTests(unittest.TestCase):
    def test_repository_hub_passes(self) -> None:
        report = validator.run_validation(ROOT)
        self.assertEqual(report["status"], "passed", report["errors"])

    def test_no_standardized_instrument_is_approved_by_default(self) -> None:
        catalog = validator.load_catalog(ROOT / "professional-assessment-hub")
        approved = [
            item["id"]
            for item in catalog["instruments"]
            if item["license_status"] != "internal_template"
            and item["digital_status"] == "approved_for_production"
        ]
        self.assertEqual(approved, [])

    def test_every_condition_has_multiple_stages_and_red_flags(self) -> None:
        catalog = validator.load_catalog(ROOT / "professional-assessment-hub")
        for condition in catalog["conditions"]:
            with self.subTest(condition=condition["id"]):
                self.assertGreaterEqual(len(condition["steps"]), 2)
                self.assertTrue(condition["red_flags"])
                for step in condition["steps"]:
                    self.assertTrue(step["completion"])
                    self.assertTrue(step["next"])

    def test_referenced_tools_exist(self) -> None:
        catalog = validator.load_catalog(ROOT / "professional-assessment-hub")
        instrument_ids = {item["id"] for item in catalog["instruments"]}
        missing = []
        for condition in catalog["conditions"]:
            for step in condition["steps"]:
                for tool in step["candidate_tools"]:
                    if tool not in instrument_ids:
                        missing.append((condition["id"], step["id"], tool))
        self.assertEqual(missing, [])

    def test_validator_rejects_public_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            hub = temp_root / "professional-assessment-hub"
            hub.mkdir(parents=True)
            source = ROOT / "professional-assessment-hub"
            for name in validator.REQUIRED_FILES:
                (hub / name).write_bytes((source / name).read_bytes())
            catalog = json.loads((hub / "catalog.json").read_text(encoding="utf-8"))
            catalog["release"]["public_navigation"] = True
            (hub / "catalog.json").write_text(
                json.dumps(catalog, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            errors = validator.validate_catalog(catalog)
            self.assertIn("public_navigation must be false", errors)

    def test_html_has_no_patient_identity_fields(self) -> None:
        errors = validator.validate_html(ROOT / "professional-assessment-hub")
        identity_errors = [item for item in errors if "forbidden patient field" in item]
        self.assertEqual(identity_errors, [])


if __name__ == "__main__":
    unittest.main()
