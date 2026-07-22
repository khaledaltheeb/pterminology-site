from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "audit_unpublished_content_v74.py"


class UnpublishedContentAuditV74Tests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="unpublished-v74-"))
        for directory in (
            ".github/workflows",
            "scripts",
            "content/i18n",
            "content/sectors",
            "assets",
            "docs",
            "data",
        ):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / ".github" / "workflows" / "validate-all-labs-v22.yml").write_text(
            "name: Validate every assessment and cognitive tool v31\n"
            "jobs:\n  build:\n    steps:\n"
            "      - run: python scripts/publish_live.py\n"
            "      - run: python scripts/apply_homepage.py\n"
            "      - run: cp content/sectors/*.json /tmp/\n",
            encoding="utf-8",
        )
        (root / "scripts" / "publish_live.py").write_text(
            'DATA = "content/live.json"\nASSET = "assets/live.js"\n', encoding="utf-8"
        )
        (root / "scripts" / "apply_homepage.py").write_text(
            'from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n'
            'PUBLISHER = ROOT / "scripts" / "publish_i18n.py"\n',
            encoding="utf-8",
        )
        (root / "scripts" / "publish_i18n.py").write_text(
            'from pathlib import Path\nROOT = Path(__file__).resolve().parents[1]\n'
            'DATA = ROOT / "content" / "i18n" / "page.json"\n',
            encoding="utf-8",
        )
        (root / "content" / "live.json").write_text('{"title":"Live"}', encoding="utf-8")
        (root / "content" / "i18n" / "page.json").write_text('{"title":"Localized"}', encoding="utf-8")
        (root / "content" / "sectors" / "family.json").write_text('{"title":"Family"}', encoding="utf-8")
        (root / "assets" / "live.js").write_text("console.log('live')", encoding="utf-8")
        (root / "content" / "unwired.json").write_text(
            '{"title":"Unwired","review_status":"ready"}', encoding="utf-8"
        )
        (root / "content" / "autism-draft.json").write_text(
            '{"title":"Sensitive","review_status":"needs-specialist-review"}', encoding="utf-8"
        )
        (root / "scripts" / "publish_unwired.py").write_text(
            'DATA = "content/unwired.json"\nASSET = "assets/unwired.js"\n', encoding="utf-8"
        )
        (root / "assets" / "unwired.js").write_text("console.log('unwired')", encoding="utf-8")
        (root / "docs" / "policy.md").write_text("# Policy", encoding="utf-8")
        (root / "data" / "registry.json").write_text('{"items":[]}', encoding="utf-8")
        return root

    def test_detects_reachable_and_unpublished_sources(self) -> None:
        root = self.make_repo()
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        completed = subprocess.run(
            ["python3", str(AUDITOR), str(root)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        report = json.loads((root / "_audit" / "unpublished-content-v74.json").read_text(encoding="utf-8"))
        reachable = set(report["reachable_files"])
        candidate_map = {item["path"]: item for item in report["candidates"]}
        print("AUDITOR_STDOUT", completed.stdout)
        print("REACHABLE", json.dumps(sorted(reachable), ensure_ascii=False))
        print("CANDIDATES", json.dumps(candidate_map, ensure_ascii=False, sort_keys=True))
        for expected in (
            "scripts/publish_live.py",
            "content/live.json",
            "assets/live.js",
            "scripts/apply_homepage.py",
            "scripts/publish_i18n.py",
            "content/i18n/page.json",
            "content/sectors/family.json",
        ):
            self.assertIn(expected, reachable, f"Missing reachable source {expected}; actual={sorted(reachable)}")
        self.assertNotIn("content/live.json", candidate_map)
        self.assertNotIn("content/i18n/page.json", candidate_map)
        self.assertNotIn("content/sectors/family.json", candidate_map)
        self.assertEqual(candidate_map["content/unwired.json"]["category"], "source-only")
        self.assertEqual(candidate_map["scripts/publish_unwired.py"]["category"], "unwired-publisher")
        self.assertEqual(candidate_map["assets/unwired.js"]["category"], "unwired-asset")
        self.assertEqual(candidate_map["content/autism-draft.json"]["category"], "blocked-review")
        self.assertEqual(candidate_map["docs/policy.md"]["category"], "documentation-only")
        self.assertEqual(candidate_map["data/registry.json"]["category"], "governance-data-only")
        self.assertTrue((root / "_audit" / "unpublished-content-v74.md").is_file())


if __name__ == "__main__":
    unittest.main()
