import tempfile
import unittest
from pathlib import Path

from scripts.audit_cross_section_links_v177 import audit


PAGE = '''<!doctype html><html lang="ar" dir="rtl"><head>
<title>{title}</title><meta name="description" content="{description}">
<link rel="canonical" href="https://khaledaltheeb.github.io/pterminology-site{route}">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebPage"}}</script>
</head><body><h1>{title}</h1>{links}</body></html>'''


class CrossSectionAuditTests(unittest.TestCase):
    def make_site(self, pages):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        for route, links in pages.items():
            target = root / ("index.html" if route == "/" else route.strip("/") + "/index.html")
            target.parent.mkdir(parents=True, exist_ok=True)
            anchors = "".join(f'<a href="/pterminology-site{href}">رابط سياقي مفيد</a>' for href in links)
            target.write_text(PAGE.format(
                title="عنوان عربي مفيد ومتكامل للصفحة",
                description="وصف عربي واضح ومفيد يشرح غرض الصفحة ومحتواها والجمهور المستهدف دون حشو أو ادعاءات غير موثقة، ويقود المستخدم إلى الخطوة المناسبة بأمان.",
                route=route,
                links=anchors,
            ), encoding="utf-8")
        return temp, root

    def test_detects_orphan_and_missing_cross_section_discovery(self):
        temp, root = self.make_site({"/": ["/encyclopedia/"], "/encyclopedia/": [], "/blog/example/": []})
        self.addCleanup(temp.cleanup)
        report = audit(root)
        row = next(page for page in report["pages"] if page["route"] == "/blog/example/")
        self.assertIn("orphan", row["issues"])
        self.assertIn("no_cross_section_discovery", row["issues"])
        self.assertEqual(row["decision"], "improve")

    def test_cross_section_link_removes_discovery_warning(self):
        temp, root = self.make_site({"/": ["/encyclopedia/"], "/encyclopedia/": ["/blog/example/"], "/blog/example/": ["/encyclopedia/"]})
        self.addCleanup(temp.cleanup)
        report = audit(root)
        row = next(page for page in report["pages"] if page["route"] == "/blog/example/")
        self.assertNotIn("orphan", row["issues"])
        self.assertNotIn("no_cross_section_discovery", row["issues"])
        self.assertIn("encyclopedia", row["incoming_sections"])

    def test_broken_link_is_critical(self):
        temp, root = self.make_site({"/": ["/care-guides/missing/"]})
        self.addCleanup(temp.cleanup)
        report = audit(root)
        row = next(page for page in report["pages"] if page["route"] == "/")
        self.assertIn("broken_internal_links", row["issues"])
        self.assertEqual(row["severity"], "critical")
        self.assertEqual(row["decision"], "fix-before-publish")

    def test_metadata_and_schema_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "index.html").write_text('<html><head><title>قصير</title></head><body><h1>أ</h1><h1>ب</h1></body></html>', encoding="utf-8")
            report = audit(root)
            row = report["pages"][0]
            self.assertIn("weak_title", row["issues"])
            self.assertIn("weak_meta_description", row["issues"])
            self.assertIn("invalid_h1_count", row["issues"])
            self.assertIn("missing_canonical", row["issues"])
            self.assertIn("missing_json_ld", row["issues"])


if __name__ == "__main__":
    unittest.main()
