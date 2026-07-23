import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "normalize_internal_base_paths_v198.py"

spec = importlib.util.spec_from_file_location("base_paths_v198", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class InternalBasePathsV198Tests(unittest.TestCase):
    def make_site(self, root: Path) -> None:
        (root / "api").mkdir(parents=True)
        (root / "assets").mkdir(parents=True)
        (root / "index.html").write_text(
            '''<!doctype html><html><head>
<link rel="canonical" href="https://khaledaltheeb.github.io/care-guides/">
<meta property="og:url" content="https://khaledaltheeb.github.io/start-here/">
<link rel="manifest" href="/manifest.webmanifest">
</head><body>
<a href="/care-guides/">الأدلة</a>
<a href="https://khaledaltheeb.github.io/pterminology-site/start-here/">ابدأ</a>
<a href="https://example.org/care-guides/">خارجي</a>
<img src=/assets/logo.svg alt="">
<style>.hero{background:url(/assets/hero.svg)}</style>
</body></html>''',
            encoding="utf-8",
        )
        (root / "sitemap.xml").write_text(
            '''<?xml version="1.0"?><urlset><url><loc>https://khaledaltheeb.github.io/care-guides/</loc></url></urlset>''',
            encoding="utf-8",
        )
        (root / "manifest.webmanifest").write_text(
            json.dumps(
                {
                    "start_url": "/",
                    "scope": "/",
                    "icons": [{"src": "/assets/icon.png"}],
                }
            ),
            encoding="utf-8",
        )
        (root / "assets" / "app.js").write_text(
            'const route="/start-here/"; const api="https://khaledaltheeb.github.io/api/info.json";',
            encoding="utf-8",
        )

    def test_normalizes_absolute_root_relative_css_json_and_unquoted_attributes(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            report = module.normalize_site(site)
            self.assertEqual(report["status"], "passed")
            self.assertGreaterEqual(report["replacements"], 9)
            self.assertEqual(report["remaining_error_files"], 0)

            html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn(
                "https://khaledaltheeb.github.io/pterminology-site/care-guides/",
                html,
            )
            self.assertIn('href="/pterminology-site/care-guides/"', html)
            self.assertIn('href="/pterminology-site/manifest.webmanifest"', html)
            self.assertIn('src=/pterminology-site/assets/logo.svg', html)
            self.assertIn('url(/pterminology-site/assets/hero.svg)', html)
            self.assertIn("https://example.org/care-guides/", html)
            self.assertNotIn(
                "https://khaledaltheeb.github.io/pterminology-site/pterminology-site/",
                html,
            )

            manifest = json.loads((site / "manifest.webmanifest").read_text(encoding="utf-8"))
            self.assertEqual(manifest["start_url"], "/pterminology-site/")
            self.assertEqual(manifest["scope"], "/pterminology-site/")
            self.assertEqual(manifest["icons"][0]["src"], "/pterminology-site/assets/icon.png")

            script = (site / "assets" / "app.js").read_text(encoding="utf-8")
            self.assertIn('"/pterminology-site/start-here/"', script)
            self.assertIn(
                "https://khaledaltheeb.github.io/pterminology-site/api/info.json",
                script,
            )

    def test_is_idempotent_and_writes_audit_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            first = module.normalize_site(site)
            second = module.normalize_site(site)
            self.assertGreater(first["replacements"], 0)
            self.assertEqual(second["replacements"], 0)
            self.assertEqual(second["files_changed"], 0)
            stored = json.loads(
                (site / "api" / "internal-base-paths-v198.json").read_text(encoding="utf-8")
            )
            self.assertEqual(stored["status"], "passed")
            self.assertEqual(stored["required_base_path"], "/pterminology-site/")

    def test_check_only_fails_to_hide_bad_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = Path(temporary)
            self.make_site(site)
            report = module.normalize_site(site, check_only=True)
            self.assertEqual(report["status"], "failed")
            self.assertGreater(report["remaining_error_files"], 0)
            html = (site / "index.html").read_text(encoding="utf-8")
            self.assertIn("https://khaledaltheeb.github.io/care-guides/", html)


if __name__ == "__main__":
    unittest.main()
