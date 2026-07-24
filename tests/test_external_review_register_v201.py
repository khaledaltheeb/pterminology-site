from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts import validate_external_review_register_v201 as validator

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "external-review-register-v201.json"


class ExternalReviewRegisterV201Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(REGISTER.read_text(encoding="utf-8"))

    def test_current_register_matches_every_external_block(self) -> None:
        report = validator.validate_register(copy.deepcopy(self.payload), ROOT)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["blocked_source_count"], 3)
        self.assertEqual(report["registered_item_count"], 3)
        self.assertTrue(report["all_publication_blocks_active"])
        self.assertTrue(report["all_decisions_pending"])

    def test_cannot_drop_a_blocked_source(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["items"] = payload["items"][:-1]
        with self.assertRaisesRegex(validator.ValidationError, "missing from register"):
            validator.validate_register(payload, ROOT)

    def test_cannot_claim_approval_without_status_change_evidence(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["items"][0]["decision"] = "approve-within-defined-scope"
        with self.assertRaisesRegex(validator.ValidationError, "decision must remain awaiting-independent-review"):
            validator.validate_register(payload, ROOT)

    def test_cannot_reduce_reviewer_roles_or_acceptance_criteria(self) -> None:
        payload = copy.deepcopy(self.payload)
        payload["items"][1]["required_reviewer_roles"] = payload["items"][1]["required_reviewer_roles"][:2]
        payload["items"][2]["acceptance_criteria"] = payload["items"][2]["acceptance_criteria"][:3]
        with self.assertRaises(validator.ValidationError) as ctx:
            validator.validate_register(payload, ROOT)
        message = str(ctx.exception)
        self.assertIn("at least four reviewer roles", message)
        self.assertIn("at least eight acceptance criteria", message)

    def test_urgent_services_remain_empty(self) -> None:
        urgent = json.loads((ROOT / "data" / "urgent-help-governance.json").read_text(encoding="utf-8"))
        self.assertEqual(urgent["review_status"], "needs-external-review")
        self.assertFalse(urgent["default_publishable"])
        self.assertEqual(urgent["services"], [])


if __name__ == "__main__":
    unittest.main()
