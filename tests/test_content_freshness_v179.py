import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.audit_content_freshness_v179 import audit, write_reports


class ContentFreshnessAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "content").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, name, payload):
        path = self.root / "content" / name
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def test_high_risk_published_record_requires_review_date_sources_and_review(self):
        self.write_json("unsafe.json", {
            "title": "صفحة صحية مرتفعة المخاطر",
            "description": "محتوى جوهري",
            "status": "published",
            "risk_level": "high",
            "review_status": "needs-specialist-review",
            "sources": [],
        })
        finding = audit(self.root, date(2026, 7, 23))[0]
        self.assertEqual(finding.decision, "fix-before-publish")
        self.assertIn("published_without_review_date", finding.codes)
        self.assertIn("high_risk_review_incomplete", finding.codes)
        self.assertIn("high_risk_without_structured_sources", finding.codes)

    def test_current_record_passes_with_structured_recent_source(self):
        self.write_json("current.json", {
            "id": "guide.current",
            "title": "دليل مراجع",
            "description": "محتوى عربي أصلي غني ومفيد",
            "status": "reviewed",
            "risk_level": "high",
            "review_status": "internally-reviewed",
            "reviewed_at": "2026-07-01",
            "sources": [{"id": "who-1", "verified_at": "2026-06-01"}],
        })
        finding = audit(self.root, date(2026, 7, 23))[0]
        self.assertEqual(finding.decision, "current")
        self.assertEqual(finding.codes, [])

    def test_overdue_review_and_stale_source_are_update_not_automatic_delete(self):
        self.write_json("stale.json", {
            "title": "محتوى قديم",
            "summary": "شرح قائم يحتاج تحديثًا",
            "status": "reviewed",
            "risk_level": "moderate",
            "review_status": "internally-reviewed",
            "reviewed_at": "2024-01-01",
            "sources": [{"verified_at": "2022-01-01"}],
        })
        finding = audit(self.root, date(2026, 7, 23))[0]
        self.assertEqual(finding.decision, "needs-update")
        self.assertIn("review_overdue", finding.codes)
        self.assertIn("stale_source_verification", finding.codes)

    def test_html_requires_title_description_canonical_and_date_modified(self):
        site = self.root / "_site"
        site.mkdir()
        (site / "index.html").write_text("<html><head><title></title></head><body></body></html>", encoding="utf-8")
        finding = audit(self.root, date(2026, 7, 23))[0]
        self.assertEqual(finding.record_type, "html-page")
        self.assertEqual(finding.decision, "fix-before-publish")
        self.assertIn("html_missing_meta_description", finding.codes)
        self.assertIn("html_missing_canonical", finding.codes)
        self.assertIn("html_missing_date_modified", finding.codes)

    def test_reports_state_advisory_not_publication_proof(self):
        self.write_json("record.json", {
            "title": "صفحة عامة",
            "description": "محتوى",
            "status": "draft",
            "review_status": "unreviewed",
            "risk_level": "low",
        })
        findings = audit(self.root, date(2026, 7, 23))
        json_path = self.root / "out.json"
        csv_path = self.root / "out.csv"
        write_reports(findings, json_path, csv_path, date(2026, 7, 23), 365, 730)
        report = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("never proves specialist review or live publication", report["publication_rule"])
        self.assertTrue(csv_path.is_file())


if __name__ == "__main__":
    unittest.main()
