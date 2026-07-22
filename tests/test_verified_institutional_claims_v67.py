import json
import unittest
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "verified-institutional-claims.json"
DOC_PATH = ROOT / "docs" / "VERIFIED_CLAIMS_REGISTRY_AR.md"


def walk_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_keys(child)


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
        self.assertIn("authorizes no expert", self.registry["publication_rule"])

    def test_claim_types_and_statuses_are_explicit(self):
        self.assertEqual(
            set(self.policy["allowed_claim_types"]),
            {
                "team_member",
                "expert_reviewer",
                "institutional_partner",
                "accreditation",
                "professional_membership",
                "impact_claim",
            },
        )
        self.assertEqual(
            set(self.policy["allowed_statuses"]),
            {"draft", "pending_verification", "verified", "expired", "revoked", "rejected"},
        )

    def test_claim_ids_are_unique(self):
        ids = [claim.get("id") for claim in self.claims]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn(None, ids)

    def test_all_claims_use_allowed_type_and_status(self):
        allowed_types = set(self.policy["allowed_claim_types"])
        allowed_statuses = set(self.policy["allowed_statuses"])
        for claim in self.claims:
            self.assertIn(claim.get("claim_type"), allowed_types)
            self.assertIn(claim.get("status"), allowed_statuses)

    def test_unverified_claims_are_not_publishable(self):
        for claim in self.claims:
            if claim.get("status") != "verified":
                self.assertFalse(claim.get("publishable", False))

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

    def test_verified_claims_have_primary_evidence(self):
        allowed_evidence = set(self.policy["required_evidence_types"])
        for claim in self.claims:
            if claim.get("status") != "verified":
                continue
            evidence = claim["evidence"]
            self.assertIn(evidence.get("type"), allowed_evidence)
            self.assertTrue(str(evidence.get("reference", "")).strip())
            if evidence.get("url"):
                parsed = urlparse(evidence["url"])
                self.assertEqual(parsed.scheme, "https")
                self.assertTrue(parsed.netloc)

    def test_attributed_verified_claims_record_consent(self):
        consent_types = {"team_member", "expert_reviewer", "institutional_partner"}
        for claim in self.claims:
            if claim.get("status") == "verified" and claim.get("claim_type") in consent_types:
                self.assertTrue(claim.get("subject_consent"))
                self.assertTrue(str(claim.get("subject_consent_reference", "")).strip())

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

    def test_verified_claims_define_bounded_publication_scope(self):
        allowed = set(self.policy["allowed_publication_surfaces"])
        for claim in self.claims:
            if claim.get("status") == "verified":
                surfaces = claim.get("allowed_surfaces")
                self.assertIsInstance(surfaces, list)
                self.assertTrue(surfaces)
                self.assertTrue(set(surfaces) <= allowed)

    def test_registry_contains_no_sensitive_public_fields(self):
        forbidden = set(self.policy["forbidden_public_fields"])
        present_keys = {key.lower() for key in walk_keys(self.registry)}
        self.assertTrue(forbidden.isdisjoint(present_keys))

    def test_empty_registry_authorizes_nothing(self):
        if not self.claims:
            self.assertFalse(self.policy["default_publishable"])
            self.assertIn("authorizes no expert", self.registry["publication_rule"])

    def test_document_states_core_prohibitions(self):
        text = DOC_PATH.read_text(encoding="utf-8")
        for phrase in [
            "ممنوع من النشر افتراضيًا",
            "شريك رسمي",
            "أثر مثبت",
            "لا ينشئ اعتمادًا أو شراكة",
        ]:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
