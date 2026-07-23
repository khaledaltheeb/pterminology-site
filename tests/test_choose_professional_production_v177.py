from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"
PUBLISHER = ROOT / "scripts" / "publish_choose_professional_v176.py"
DATA = ROOT / "content" / "v176" / "choosing-mental-health-professional-ar.json"


class ChooseProfessionalProductionTests(unittest.TestCase):
    def test_required_sources_exist(self):
        self.assertTrue(APPLY.is_file())
        self.assertTrue(PUBLISHER.is_file())
        self.assertTrue(DATA.is_file())

    def test_production_pipeline_invokes_publisher_once(self):
        text = APPLY.read_text(encoding="utf-8")
        call = 'run_publisher("publish_choose_professional_v176.py")'
        self.assertEqual(text.count(call), 1)
        self.assertIn('"choose_professional_publisher": 176', text)

    def test_publisher_runs_after_care_guide_base(self):
        text = APPLY.read_text(encoding="utf-8")
        self.assertLess(
            text.index('run_publisher("publish_care_guides_v21.py")'),
            text.index('run_publisher("publish_choose_professional_v176.py")'),
        )

    def test_publisher_targets_expected_public_route(self):
        text = PUBLISHER.read_text(encoding="utf-8")
        self.assertIn('"care-guides" / "choosing-mental-health-professional" / "index.html"', text)
        self.assertIn('sitemap-care-guides.xml', text)

    def test_pipeline_synchronizes_generated_care_guide_report(self):
        text = APPLY.read_text(encoding="utf-8")
        self.assertIn("def synchronize_care_guides_report()", text)
        self.assertEqual(text.count("synchronize_care_guides_report()"), 2)
        self.assertLess(
            text.index('run_publisher("publish_choose_professional_v176.py")'),
            text.rindex("synchronize_care_guides_report()"),
        )
        self.assertIn('report["sitemap_urls"] = len(urls)', text)
        self.assertIn('report["pages"] = len(html_pages)', text)
        self.assertIn('report["choosing_professional_guide"] = True', text)
        self.assertIn('"care_guides_report_sync": 177', text)


if __name__ == "__main__":
    unittest.main()
