import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "audit_interactive_contract_v164.py"


SAFE_PAGE = """<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>أداة</title></head>
<body><main><h1>أداة متابعة</h1>
<p>هذه أداة غير تشخيصية. اطلب مساعدة مهنية من مختص عند استمرار المشكلة.</p>
<p>البيانات خاصة وتبقى محليًا على هذا الجهاز.</p>
<form><label for="mood">المزاج</label><input id="mood" name="mood">
<button type="submit">اعرض النتيجة</button></form>
<button type="button">تصدير</button><button type="button">حذف البيانات</button>
<script>localStorage.setItem("x", "1");</script>
</main></body></html>"""

UNSAFE_PAGE = """<!doctype html>
<html lang="ar"><body><form><input name="score"><button aria-label=""></button></form>
<h1>أداة</h1><h1>نتيجة</h1><script>fetch("/collect", {method:"POST"});</script></body></html>"""


class InteractiveContractAuditTests(unittest.TestCase):
    def run_audit(self, pages, fail=False):
        with tempfile.TemporaryDirectory() as temp:
            site = Path(temp) / "site"
            site.mkdir()
            for name, content in pages.items():
                (site / name).write_text(content, encoding="utf-8")
            output = Path(temp) / "report.json"
            command = [sys.executable, str(SCRIPT), str(site), "--json", str(output)]
            if fail:
                command.append("--fail-on-critical")
            result = subprocess.run(command, text=True, capture_output=True)
            report = json.loads(output.read_text(encoding="utf-8"))
            return result, report

    def test_safe_local_tool_has_no_critical_findings(self):
        result, report = self.run_audit({"safe.html": SAFE_PAGE}, fail=True)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(report["interactive_pages"], 1)
        self.assertEqual(report["critical_findings"], 0)

    def test_unsafe_tool_is_blocked(self):
        result, report = self.run_audit({"unsafe.html": UNSAFE_PAGE}, fail=True)
        self.assertEqual(result.returncode, 2)
        findings = set(report["pages"][0]["critical"])
        self.assertIn("arabic_page_not_rtl", findings)
        self.assertIn("h1_count_not_one", findings)
        self.assertIn("unlabelled_form_controls", findings)
        self.assertIn("missing_non_diagnostic_boundary", findings)
        self.assertIn("network_transmission_api_detected", findings)

    def test_noninteractive_pages_are_ignored(self):
        result, report = self.run_audit({"index.html": "<html lang='ar' dir='rtl'><h1>مقال</h1></html>"})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report["interactive_pages"], 0)


if __name__ == "__main__":
    unittest.main()
