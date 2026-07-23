import json
import re
import tempfile
import unittest
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_audience_resource_pathways_v184.py"
FINALIZER = ROOT / "scripts" / "finalize_audience_resource_pathways_v184.py"


class AudienceResourceSeoTests(unittest.TestCase):
    def test_audience_and_resource_portals_have_distinct_descriptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = Path(tmp)
            (site / "index.html").write_text(
                '<html lang="ar" dir="rtl"><main><h1>الرئيسية</h1></main></html>',
                encoding="utf-8",
            )
            (site / "sitemap.xml").write_text(
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>',
                encoding="utf-8",
            )
            publish = run(["python", str(PUBLISHER), str(site)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(publish.returncode, 0, publish.stderr)
            finalize = run(["python", str(FINALIZER), str(site)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(finalize.returncode, 0, finalize.stderr)

            audience = (site / "audiences" / "index.html").read_text(encoding="utf-8")
            resources = (site / "resources" / "index.html").read_text(encoding="utf-8")
            pattern = re.compile(r'<meta name="description" content="([^"]+)">')
            audience_description = pattern.search(audience)
            resource_description = pattern.search(resources)
            self.assertIsNotNone(audience_description)
            self.assertIsNotNone(resource_description)
            self.assertNotEqual(audience_description.group(1), resource_description.group(1))
            self.assertIn("مكتبة عربية", resource_description.group(1))
            self.assertNotIn(audience_description.group(1), resources)

            report = json.loads(
                (site / "api" / "audience-resource-pathways-v184.json").read_text(encoding="utf-8")
            )
            self.assertTrue(report["resources_description_unique"])
            self.assertEqual(report["resources_description"], resource_description.group(1))


if __name__ == "__main__":
    unittest.main()
