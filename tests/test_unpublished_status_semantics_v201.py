from __future__ import annotations

import unittest

from scripts import audit_unpublished_content_v201 as audit


class UnpublishedStatusSemanticsV201Tests(unittest.TestCase):
    def test_safety_code_tokens_do_not_block_reachable_publisher(self) -> None:
        category, _, action = audit.classify(
            "scripts/publish_safe_wrapper.py",
            {"detected_status_tokens": ["needs-specialist-review", "built-not-published"]},
            [],
            True,
            None,
        )
        self.assertEqual(category, "production-reachable")
        self.assertEqual(action, "retain")

    def test_explicit_source_review_status_remains_blocking(self) -> None:
        category, _, action = audit.classify(
            "content/clinical-draft.json",
            {"review_status": "needs-specialist-review"},
            [],
            True,
            None,
        )
        self.assertEqual(category, "blocked-review")
        self.assertEqual(action, "do-not-publish")

    def test_explicit_nonpublished_status_requires_live_verification(self) -> None:
        category, _, action = audit.classify(
            "content/ready.json",
            {"status": "built-not-published"},
            [],
            True,
            None,
        )
        self.assertEqual(category, "wired-unconfirmed")
        self.assertEqual(action, "verify-live")


if __name__ == "__main__":
    unittest.main()
