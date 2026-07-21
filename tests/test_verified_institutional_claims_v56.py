import json
import unittest
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "verified-institutional-claims.json"
DOC_PATH = ROOT / "docs" / "VERIFIED_CLAIMS_REGISTRY_AR.md"


class VerifiedInstitutionalClaimsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        cls.policy = cls.registry["policy"]
        cls.claims = cls.registry["claims"]

    def test_registry_and_document_exist(self):
        self.assertTrue(REGISTRY_PATH.is_file())
        self.assertTrue(DOC_PATH.is_file())

    def test_default_is_deny(self):
        self.assertFalse(self.policy["default_publishable"])
        self.assertEqual(self.policy["required_status_for_publication"], "verified")

    def test_claim_types_are_explicit_and_bounded(self):
        expected = {
            "team_member",
            "expert_reviewer",
            "institutional_partner",
            "accreditation",
            "impact_claim",
        }
        self.assertEqual(set(self.policy["allowed_claim_types"]), expected)

    def test_no_claim_is_pre_authorized_without_evidence(self):
        for claim in self.claims:
            self.assertNotEqual(claim.get("status"), "verified" if not claim.get("evidence") else None)

    def test_verified_claims_have_required_fields(self):
        required = {
            "id",
            "claim_type",
            "claim_text",
            "status",
            "evidence",
            "reviewed_by",
            "verified_at",
            "review_due_at",
            "allowed_surfaces",
        }
        for claim in self.claims:
            if claim.get("status") == "verified":
                self.assertFalse(required - set(claim), f"Missing fields for {claim.get('id')}")

    def test_verified_claims_use_allowed_types(self):
        allowed = set(self.policy["allowed_claim_types"])
        for claim in self.claims:
            self.assertIn(claim.get("claim_type"), allowed)

    def test_verified_claims_have_primary_evidence(self):
        allowed_evidence = set(self.policy["required_evidence_types"])
        for claim in self.claims:
            if claim.get("status") != "verified":
                continue
            evidence = claim["evidence"]
            self.assertIn(evidence.get("type"), allowed_evidence)
            self.assertTrue(evidence.get("reference"))
            if evidence.get("url"):
                parsed = urlparse(evidence["url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.netloc)

    def test_verified_claims_have_real_reviewer_name(self):
        forbidden = {"", "unknown", "tbd", "ai", "system", "automation", "غير معروف"}
        for claim in self.claims:
            if claim.get("status") == "verified":
                reviewer = str(claim.get("reviewed_by", "")).strip().lower()
                self.assertNotIn(reviewer, forbidden)
                self.assertGreaterEqual(len(reviewer.split()), 2)

    def test_verified_claims_have_valid_review_dates(self):
        max_age = int(self.policy["maximum_verification_age_days"])
        for claim in self.claims:
            if claim.get("status") != "verified":
                continue
            verified_at = datetime.strptime(claim["verified_at"], "%Y-%m-%d").date()
            review_due_at = datetime.strptime(claim["review_due_at"], "%Y-%m-%d").date()
            self.assertGreater(review_due_at, verified_at)
            self.assertLessEqual((review_due_at - verified_at).days, max_age)
            self.assertGreaterEqual(review_due_at, date.today())

    def test_verified_claims_define_publication_scope(self):
        for claim in self.claims:
            if claim.get("status") == "verified":
                surfaces = claim.get("allowed_surfaces")
                self.assertIsInstance(surfaces, list)
                self.assertTrue(surfaces)
                self.assertTrue(all(isinstance(item, str) and item.strip() for item in surfaces))

    def test_registry_contains_no_sensitive_document_payloads(self):
        serialized = json.dumps(self.registry, ensure_ascii=False).lower()
        forbidden = ["national_id", "passport_number", "signature_image", "private_phone"]
        for token in forbidden:
            self.assertNotIn(token, serialized)

    def test_empty_registry_authorizes_nothing(self):
        if not self.claims:
            self.assertIn("no expert, partner, accreditation, or impact claim is authorized", self.registry["publication_rule"])


if __name__ == "__main__":
    unittest.main()
