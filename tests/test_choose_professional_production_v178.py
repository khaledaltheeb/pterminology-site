from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APPLY = ROOT / "scripts" / "apply_homepage_v20.py"
CORE = ROOT / "scripts" / "publish_care_guides_v21.py"
PUBLISHER = ROOT / "scripts" / "publish_choose_professional_v176.py"
DATA = ROOT / "content" / "v176" / "choosing-mental-health-professional-ar.json"


class ChooseProfessionalProductionV178Tests(unittest.TestCase):
    def test_required_sources_exist(self):
        self.assertTrue(APPLY.is_file())
        self.assertTrue(CORE.is_file())
        self.assertTrue(PUBLISHER.is_file())
        self.assertTrue(DATA.is_file())

    def test_both_latest_publishers_are_preserved(self):
        text = APPLY.read_text(encoding="utf-8")
        self.assertEqual(text.count('run_publisher("publish_choose_professional_v176.py")'), 1)
        self.assertEqual(text.count('run_publisher("publish_start_here_v176.py")'), 1)
        self.assertIn('"choose_professional_publisher": 176', text)
        self.assertIn('"start_here_publisher": 176', text)

    def test_order_and_report_sync(self):
        text = APPLY.read_text(encoding="utf-8")
        care = text.index('run_publisher("publish_care_guides_v21.py")')
        choose = text.index('run_publisher("publish_choose_professional_v176.py")')
        sync = text.rindex("synchronize_care_guides_report()")
        start = text.index('run_publisher("publish_start_here_v176.py")')
        self.assertLess(care, choose)
        self.assertLess(choose, sync)
        self.assertLess(sync, start)
        self.assertIn('report["sitemap_urls"] = len(urls)', text)
        self.assertIn('report["pages"] = len(html_pages)', text)
        self.assertIn('report["choosing_professional_guide"] = True', text)
        self.assertIn('"care_guides_report_sync": 178', text)

    def test_core_publisher_preserves_valid_extension_pages(self):
        text = CORE.read_text(encoding="utf-8")
        self.assertIn("def extension_urls()", text)
        self.assertIn("core_urls + extension_urls()", text)
        self.assertIn("sitemap_url_count = update_sitemaps(guides)", text)
        self.assertIn('"sitemap_urls": sitemap_url_count', text)
        self.assertIn('"extension_guides_preserved"', text)
        self.assertNotIn('"sitemap_urls": len(guides) + 1', text)

    def test_expected_public_route_and_sitemap(self):
        text = PUBLISHER.read_text(encoding="utf-8")
        self.assertIn('"care-guides" / "choosing-mental-health-professional" / "index.html"', text)
        self.assertIn('sitemap-care-guides.xml', text)


if __name__ == "__main__":
    unittest.main()
