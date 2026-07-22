import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "audit-validated-production-content-v158.yml"


class ValidatedProductionInventoryWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_uses_exact_successful_main_production_run(self):
        for marker in (
            "workflow_run:",
            "Validate every assessment and cognitive tool v31",
            "github.event.workflow_run.conclusion == 'success'",
            "github.event.workflow_run.event == 'push'",
            "github.event.workflow_run.head_branch == 'main'",
            "ref: ${{ github.event.workflow_run.head_sha }}",
        ):
            self.assertIn(marker, self.text)

    def test_downloads_exact_validated_artifact_with_read_only_permissions(self):
        self.assertIn("actions: read", self.text)
        self.assertIn("contents: read", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertIn("name: validated-production-site", self.text)
        self.assertIn("run-id: ${{ github.event.workflow_run.id }}", self.text)
        self.assertIn("github-token: ${{ secrets.GITHUB_TOKEN }}", self.text)

    def test_provenance_and_advisory_policy_are_enforced(self):
        for marker in (
            "test -f _site/deployment.json",
            "python scripts/audit_content_inventory_v69.py _site",
            "automatic_delete_or_noindex",
            "required_human_review_for",
            "recorded_sha == expected_sha",
            "validated-production-content-inventory-v158",
            "content-inventory-v69.json",
            "content-inventory-v69.csv",
            "provenance.json",
        ):
            self.assertIn(marker, self.text)

    def test_does_not_publish_or_mutate_repository(self):
        forbidden = (
            "git push",
            "merge_pull_request",
            "actions/upload-pages-artifact",
            "actions/deploy-pages",
            "contents: write",
        )
        for marker in forbidden:
            self.assertNotIn(marker, self.text)


if __name__ == "__main__":
    unittest.main()
