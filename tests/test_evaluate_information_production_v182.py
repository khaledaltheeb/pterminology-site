import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"
PUBLISHER = ROOT / "scripts" / "publish_evaluate_mental_health_information_v181.py"
DATA = ROOT / "content" / "v181" / "evaluate-mental-health-information-ar.json"


class EvaluateInformationProductionV182Tests(unittest.TestCase):
    def test_required_sources_exist(self):
        self.assertTrue(APPLY.is_file())
        self.assertTrue(PUBLISHER.is_file())
        self.assertTrue(DATA.is_file())

    def test_production_pipeline_invokes_publisher_once_and_registers_sitemap(self):
        text = APPLY.read_text(encoding="utf-8")
        self.assertEqual(text.count('run_publisher("publish_evaluate_mental_health_information_v181.py")'), 1)
        self.assertEqual(text.count('register_sitemap("sitemap-evaluate-mental-health-information.xml")'), 1)
        self.assertIn('"evaluate_information_publisher": 181', text)
        self.assertIn('"evaluate_information_sitemap_sync": 182', text)

    def test_order_preserves_existing_centers_and_start_here(self):
        text = APPLY.read_text(encoding="utf-8")
        special = text.index('run_publisher("publish_special_needs_v73.py")')
        choose = text.index('run_publisher("publish_choose_professional_v176.py")')
        evaluate = text.index('run_publisher("publish_evaluate_mental_health_information_v181.py")')
        start_here = text.index('run_publisher("publish_start_here_v176.py")')
        self.assertLess(special, choose)
        self.assertLess(choose, evaluate)
        self.assertLess(evaluate, start_here)

    def test_content_is_moderate_risk_and_does_not_claim_external_review(self):
        data = json.loads(DATA.read_text(encoding="utf-8"))
        self.assertEqual(data["risk_level"], "moderate")
        self.assertEqual(data["status"], "internally-reviewed")
        self.assertNotEqual(data.get("review_status"), "externally-reviewed")
        self.assertFalse(data.get("externally_reviewed", False))
        self.assertFalse(data.get("specialist_review_claimed", False))
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertNotIn('"status": "externally-reviewed"', serialized)


if __name__ == "__main__":
    unittest.main()
