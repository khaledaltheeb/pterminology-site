from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "audit_unpublished_content_v201.py"


class UnpublishedContentAuditV201Tests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="unpublished-v201-"))
        for directory in (
            ".github/workflows",
            "scripts",
            "content",
            "assets",
            "docs",
            "data",
            "provider-assessment-demo",
        ):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / ".github/workflows/validate-all-labs-v22.yml").write_text(
            "name: Validate every assessment and cognitive tool v31\n"
            "jobs:\n  build:\n    steps:\n"
            "      - run: python scripts/publish_live.py\n"
            "      - run: python scripts/apply_homepage.py\n",
            encoding="utf-8",
        )
        (root / "scripts/publish_live.py").write_text(
            'DATA = "content/live.json"\nASSET = "assets/live.js"\n', encoding="utf-8"
        )
        (root / "scripts/apply_homepage.py").write_text(
            "from pathlib import Path\n"
            "def run_publisher(name): pass\n"
            "def restore_static_route(name): pass\n"
            'run_publisher("publish_dynamic.py")\n'
            'INDIRECT = Path(__file__).with_name("publish_indirect.py")\n'
            'restore_static_route("provider-assessment-demo")\n',
            encoding="utf-8",
        )
        (root / "scripts/publish_dynamic.py").write_text(
            'DATA = "content/dynamic.json"\nimport publish_imported\n', encoding="utf-8"
        )
        (root / "scripts/publish_imported.py").write_text(
            'DATA = "content/imported.json"\n', encoding="utf-8"
        )
        (root / "scripts/publish_indirect.py").write_text(
            'DATA = "content/indirect.json"\n', encoding="utf-8"
        )
        (root / "content/live.json").write_text(
            '{"title":"Live","status":"published"}', encoding="utf-8"
        )
        (root / "content/dynamic.json").write_text(
            '{"title":"Dynamic","status":"internally-reviewed"}', encoding="utf-8"
        )
        (root / "content/imported.json").write_text(
            '{"title":"Imported","status":"internally-reviewed"}', encoding="utf-8"
        )
        (root / "content/indirect.json").write_text(
            '{"title":"Indirect","status":"internally-reviewed"}', encoding="utf-8"
        )
        (root / "assets/live.js").write_text("console.log('live')", encoding="utf-8")
        (root / "provider-assessment-demo/index.html").write_text(
            '<!doctype html><script src="app.js"></script>', encoding="utf-8"
        )
        (root / "provider-assessment-demo/app.js").write_text(
            "console.log('assessment')", encoding="utf-8"
        )
        (root / "content/unwired.json").write_text(
            '{"title":"Unwired","status":"built-not-published"}', encoding="utf-8"
        )
        (root / "scripts/publish_unwired.py").write_text(
            'DATA = "content/unwired.json"\nASSET = "assets/unwired.js"\n', encoding="utf-8"
        )
        (root / "assets/unwired.js").write_text("console.log('unwired')", encoding="utf-8")
        (root / "scripts/publish_superseded.py").write_text(
            'DATA = "content/unwired.json"\n', encoding="utf-8"
        )
        (root / "content/autism-draft.json").write_text(
            '{"title":"Autism draft","review_status":"needs-specialist-review"}', encoding="utf-8"
        )
        (root / "content/special-needs-draft.json").write_text(
            '{"title":"Special needs draft","review_status":"needs-external-review"}', encoding="utf-8"
        )
        (root / "docs/policy.md").write_text("# Policy", encoding="utf-8")
        (root / "data/registry.json").write_text('{"items":[]}', encoding="utf-8")
        (root / "data/recovery-dispositions-v201.json").write_text(
            json.dumps(
                {
                    "version": 201,
                    "dispositions": [
                        {
                            "path": "scripts/publish_superseded.py",
                            "disposition": "superseded",
                            "recommended_action": "retain-history",
                            "reason": "Replaced by a newer publisher",
                            "replacements": ["scripts/publish_dynamic.py"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_classifies_unpublished_and_blocked_content(self) -> None:
        root = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        subprocess.run(["python3", str(AUDITOR), str(root)], cwd=ROOT, check=True)
        report = json.loads((root / "_audit/unpublished-content-v201.json").read_text(encoding="utf-8"))
        items = {item["path"]: item for item in report["items"]}
        self.assertEqual(items["content/live.json"]["category"], "production-reachable")
        self.assertEqual(items["scripts/publish_dynamic.py"]["category"], "production-reachable")
        self.assertEqual(items["content/dynamic.json"]["category"], "production-reachable")
        self.assertEqual(items["scripts/publish_imported.py"]["category"], "production-reachable")
        self.assertEqual(items["content/imported.json"]["category"], "production-reachable")
        self.assertEqual(items["scripts/publish_indirect.py"]["category"], "production-reachable")
        self.assertEqual(items["content/indirect.json"]["category"], "production-reachable")
        self.assertIn("provider-assessment-demo/index.html", report["reachable_files"])
        self.assertIn("provider-assessment-demo/app.js", report["reachable_files"])
        self.assertEqual(items["content/unwired.json"]["category"], "source-only")
        self.assertEqual(items["scripts/publish_unwired.py"]["category"], "unwired-publisher")
        self.assertEqual(items["assets/unwired.js"]["category"], "unwired-asset")
        self.assertEqual(items["scripts/publish_superseded.py"]["category"], "superseded")
        self.assertEqual(items["scripts/publish_superseded.py"]["recommended_action"], "retain-history")
        self.assertEqual(report["disposition_count"], 1)
        self.assertEqual(items["content/autism-draft.json"]["category"], "blocked-review")
        self.assertEqual(items["content/autism-draft.json"]["recommended_action"], "do-not-publish")
        self.assertEqual(items["content/special-needs-draft.json"]["category"], "blocked-review")
        self.assertEqual(items["content/special-needs-draft.json"]["recommended_action"], "do-not-publish")
        self.assertEqual(items["docs/policy.md"]["category"], "documentation-only")
        self.assertEqual(items["data/registry.json"]["category"], "governance-data-only")
        self.assertTrue((root / "_audit/unpublished-content-v201.md").is_file())

    def test_detects_wired_but_unconfirmed_status_without_false_published_token(self) -> None:
        root = self.make_repo()
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / "content/live.json").write_text(
            '{"title":"Live","status":"built-not-published"}', encoding="utf-8"
        )
        subprocess.run(["python3", str(AUDITOR), str(root)], cwd=ROOT, check=True)
        report = json.loads((root / "_audit/unpublished-content-v201.json").read_text(encoding="utf-8"))
        item = next(item for item in report["items"] if item["path"] == "content/live.json")
        self.assertEqual(item["category"], "wired-unconfirmed")
        self.assertEqual(item["recommended_action"], "verify-live")
        tokens = item["metadata"]["detected_status_tokens"]
        self.assertIn("built-not-published", tokens)
        self.assertNotIn("published", tokens)


if __name__ == "__main__":
    unittest.main()
