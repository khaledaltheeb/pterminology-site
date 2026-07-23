import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data" / "publisher-run-ledger-v185.json"


class PublisherRunLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(LEDGER.read_text(encoding="utf-8"))

    def test_exact_ten_publishers_and_issue_mapping(self):
        publishers = self.data["publishers"]
        self.assertEqual(len(publishers), 10)
        self.assertEqual([item["id"] for item in publishers], list(range(1, 11)))
        self.assertEqual([item["issue"] for item in publishers], list(range(96, 106)))
        self.assertEqual(self.data["governing_issues"], list(range(95, 106)))

    def test_no_unverified_item_is_publishable(self):
        self.assertTrue(all(item["publishable_now"] is False for item in self.data["publishers"]))
        rule = self.data["publication_rule"]
        for marker in ["GitHub Pages", "deployment.json", "live files", "merged SHA"]:
            self.assertIn(marker, rule)

    def test_each_publisher_has_action_and_blocker(self):
        allowed_states = {
            "blocked-stale-base",
            "blocked-specialist-review",
            "blocked-conflict-and-review",
            "ready-for-safe-audit",
            "ready-for-nonclinical-draft",
        }
        for item in self.data["publishers"]:
            self.assertIn(item["state"], allowed_states)
            self.assertGreaterEqual(len(item["next_action"]), 80)
            self.assertIsInstance(item["active_pr"], int)

    def test_safe_parallel_work_is_nonclinical(self):
        work = " ".join(self.data["safe_parallel_work"])
        self.assertIn("dictionary", work.lower())
        self.assertIn("non-clinical", work.lower())
        self.assertNotIn("publish postpartum", work.lower())
        self.assertNotIn("publish anxiety", work.lower())

    def test_blocked_prs_match_all_active_publisher_prs(self):
        blocked = set(self.data["not_authorized_for_publication"])
        active = {item["active_pr"] for item in self.data["publishers"]}
        expected = {92, 108, 109, 110, 111, 112, 113, 115, 116, 125}
        self.assertEqual(blocked, active)
        self.assertEqual(blocked, expected)


if __name__ == "__main__":
    unittest.main()
