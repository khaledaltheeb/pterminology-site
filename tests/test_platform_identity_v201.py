from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "enforce_platform_identity_v201.py"


class PlatformIdentityV201Tests(unittest.TestCase):
    def make_site(self) -> Path:
        site = Path(tempfile.mkdtemp(prefix="platform-identity-v201-"))
        self.addCleanup(lambda: shutil.rmtree(site, ignore_errors=True))
        (site / "nested").mkdir()
        (site / "index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>الرئيسية</title></head>'
            '<body><main><h1>خدمات المعاقين</h1><p>دعم معاق وأسرته.</p></main></body></html>',
            encoding="utf-8",
        )
        (site / "nested/index.html").write_text(
            '<!doctype html><html lang="ar" dir="rtl"><head><title>صفحة</title></head><body>'
            '<header><nav>تنقل</nav></header><main><h1>صفحة قائمة</h1></main><footer>تذييل</footer></body></html>',
            encoding="utf-8",
        )
        return site

    def test_replaces_rejected_labels_and_adds_missing_shell(self) -> None:
        site = self.make_site()
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        homepage = (site / "index.html").read_text(encoding="utf-8")
        existing = (site / "nested/index.html").read_text(encoding="utf-8")
        self.assertNotIn("المعاقين", homepage)
        self.assertNotIn(">معاق<", homepage)
        self.assertIn("ذوي الاحتياجات الخاصة", homepage)
        self.assertIn('data-platform-shell="header"', homepage)
        self.assertIn('data-platform-shell="footer"', homepage)
        self.assertIn("منصة الصحة النفسية وذوي الاحتياجات الخاصة", homepage)
        self.assertEqual(existing.count("<header"), 1)
        self.assertEqual(existing.count("<footer"), 1)
        report = json.loads((site / "api/platform-identity-v201.json").read_text(encoding="utf-8"))
        self.assertEqual(report["pages"], 2)
        self.assertEqual(report["headers_added"], 1)
        self.assertEqual(report["footers_added"], 1)
        self.assertGreaterEqual(report["language_replacements"], 2)
        self.assertEqual(report["remaining_banned_pages"], [])
        self.assertEqual(report["missing_header_pages"], [])
        self.assertEqual(report["missing_footer_pages"], [])

    def test_is_idempotent(self) -> None:
        site = self.make_site()
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        first = (site / "index.html").read_text(encoding="utf-8")
        subprocess.run(["python3", str(SCRIPT), str(site)], cwd=ROOT, check=True)
        second = (site / "index.html").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        self.assertEqual(second.count('data-platform-shell="header"'), 1)
        self.assertEqual(second.count('data-platform-shell="footer"'), 1)
        self.assertEqual(second.count("platform-shell-v201-style"), 1)


if __name__ == "__main__":
    unittest.main()
