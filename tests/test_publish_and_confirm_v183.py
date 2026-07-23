import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "publish_and_confirm_v183.py"
WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "publish-and-confirm-every-main-v183.yml"
)

spec = importlib.util.spec_from_file_location(
    "publish_and_confirm_v183", SCRIPT_PATH
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def write_site(root: Path, commit: str) -> Path:
    site = root / "_site"
    site.mkdir()
    files = {
        "index.html": b"<h1>home</h1>",
        "sitemap.xml": b"<urlset></urlset>",
        "manifest.webmanifest": b'{"name":"site"}',
        "sw.js": b"self.addEventListener('fetch',()=>{})",
        "new/index.html": b"<h1>new</h1>",
    }
    for relative, body in files.items():
        path = site / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)

    artifacts = {
        relative: {
            "sha256": hashlib.sha256((site / relative).read_bytes()).hexdigest(),
            "bytes": (site / relative).stat().st_size,
        }
        for relative in (
            "index.html",
            "sitemap.xml",
            "manifest.webmanifest",
            "sw.js",
        )
    }
    (site / "deployment.json").write_text(
        json.dumps(
            {
                "schema_version": 29,
                "commit": commit,
                "workflow_run": "123",
                "artifacts": artifacts,
            }
        ),
        encoding="utf-8",
    )
    return site


class PublishAndConfirmTests(unittest.TestCase):
    def test_workflow_runs_only_after_successful_main_validation(self):
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn(
            'workflows: ["Validate every assessment and cognitive tool v31"]',
            text,
        )
        self.assertIn(
            "github.event.workflow_run.conclusion == 'success'", text
        )
        self.assertIn("github.event.workflow_run.head_branch == 'main'", text)
        self.assertIn("actions/download-artifact@v4", text)
        self.assertIn("actions/upload-pages-artifact@v4", text)
        self.assertIn("actions/deploy-pages@v4", text)
        self.assertIn("publish_and_confirm_v183.py verify", text)

    def test_bootstrap_prepares_manifest_and_critical_live_checks(self):
        commit = "a" * 40
        with tempfile.TemporaryDirectory() as temporary:
            site = write_site(Path(temporary), commit)
            with patch.object(module, "fetch_json_optional", return_value=None):
                module.prepare(site, commit, "https://example.test/site/")
            manifest = json.loads((site / module.MANIFEST_NAME).read_text())
            changes = json.loads((site / module.CHANGESET_PATH).read_text())
            self.assertEqual(manifest["commit"], commit)
            self.assertEqual(manifest["file_count"], 6)
            self.assertEqual(changes["verification_mode"], "bootstrap")
            self.assertEqual(
                set(changes["verify_paths"]),
                {
                    "index.html",
                    "sitemap.xml",
                    "manifest.webmanifest",
                    "sw.js",
                    "deployment.json",
                },
            )

    def test_delta_tracks_every_changed_added_and_deleted_file(self):
        commit = "b" * 40
        with tempfile.TemporaryDirectory() as temporary:
            site = write_site(Path(temporary), commit)
            previous = {
                "commit": "c" * 40,
                "files": {
                    "index.html": {
                        "sha256": module.sha256_file(site / "index.html"),
                        "bytes": (site / "index.html").stat().st_size,
                    },
                    "new/index.html": {"sha256": "wrong", "bytes": 1},
                    "deleted/index.html": {"sha256": "old", "bytes": 5},
                },
            }
            with patch.object(
                module, "fetch_json_optional", return_value=previous
            ):
                module.prepare(site, commit, "https://example.test/site/")
            changes = json.loads((site / module.CHANGESET_PATH).read_text())
            self.assertEqual(changes["verification_mode"], "delta")
            self.assertIn("new/index.html", changes["verify_paths"])
            self.assertIn("deployment.json", changes["verify_paths"])
            self.assertIn("deleted/index.html", changes["deleted"])
            self.assertNotIn("index.html", changes["verify_paths"])

    def test_deployment_stamp_must_match_exact_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            site = write_site(Path(temporary), "d" * 40)
            with self.assertRaises(SystemExit):
                module.validate_deployment_stamp(site, "e" * 40)

    def test_live_file_requires_matching_hash_and_size(self):
        expected_body = b"published"
        expected = {
            "sha256": hashlib.sha256(expected_body).hexdigest(),
            "bytes": len(expected_body),
        }
        with patch.object(
            module,
            "fetch_bytes",
            return_value=(
                200,
                expected_body,
                {"content-type": "text/html"},
            ),
        ):
            result = module.verify_one_file(
                "https://example.test/site/",
                "page/index.html",
                expected,
                "f" * 40,
                attempts=1,
                delay=0,
            )
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["sha256"], expected["sha256"])

    def test_success_status_is_reserved_for_live_confirmation(self):
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('"status": "published-and-live-confirmed"', text)
        self.assertIn("live_commit_not_confirmed", text)
        self.assertIn("live_file_mismatch", text)
        self.assertIn("deleted_file_still_live", text)


if __name__ == "__main__":
    unittest.main()
