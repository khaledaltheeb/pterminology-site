from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from service.provider_assessment import (
    ActorContextFactory,
    PermissionDenied,
    ProviderAuthorizationSnapshot,
    VerifiedIdentityClaims,
)


NOW = datetime(2026, 7, 23, 18, 0, tzinfo=timezone.utc)


class Directory:
    def __init__(
        self,
        authorization: ProviderAuthorizationSnapshot,
        *,
        revoked: frozenset[str] = frozenset(),
    ) -> None:
        self.authorization = authorization
        self.revoked = revoked

    def get_provider_authorization(
        self,
        provider_id: str,
        institution_id: str,
    ) -> ProviderAuthorizationSnapshot:
        return self.authorization

    def is_token_revoked(self, token_id: str) -> bool:
        return token_id in self.revoked


class ActorContextFactoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.authorization = ProviderAuthorizationSnapshot(
            provider_id="PROV-TEST01",
            institution_id="INST-TEST01",
            active=True,
            authorized_roles=frozenset(
                {"provider", "case_lead", "institution_auditor"}
            ),
            professional_license_verified=True,
            professional_license_reference="LICENSE:TEST:0001",
            assigned_case_ids=frozenset({"CASE-000001"}),
            audit_scope="institution",
        )
        self.claims = VerifiedIdentityClaims(
            token_id="TOKEN-000001",
            issuer="https://identity.example.invalid",
            audience="provider-assessment-service",
            subject_reference="SUBJECT:OPAQUE:0001",
            provider_id="PROV-TEST01",
            institution_id="INST-TEST01",
            asserted_roles=frozenset(
                {"provider", "case_lead", "clinical_reviewer"}
            ),
            authenticated_at=NOW - timedelta(minutes=10),
            expires_at=NOW + timedelta(minutes=50),
            mfa_verified=True,
        )

    def factory(self, directory: Directory | None = None) -> ActorContextFactory:
        return ActorContextFactory(
            directory or Directory(self.authorization),
            trusted_issuer="https://identity.example.invalid",
            expected_audience="provider-assessment-service",
            maximum_authentication_age=timedelta(hours=2),
        )

    def assert_denied(self, claims: VerifiedIdentityClaims, code: str, *, directory=None) -> None:
        with self.assertRaises(PermissionDenied) as raised:
            self.factory(directory).build(claims, now=NOW)
        self.assertEqual(raised.exception.code, code)

    def test_effective_roles_are_intersection_not_token_union(self) -> None:
        actor = self.factory().build(self.claims, now=NOW)
        self.assertEqual(actor.roles, frozenset({"provider", "case_lead"}))
        self.assertNotIn("clinical_reviewer", actor.roles)
        self.assertIsNone(actor.audit_scope)
        self.assertEqual(actor.assigned_case_ids, frozenset({"CASE-000001"}))

    def test_audit_scope_requires_both_authorization_and_effective_role(self) -> None:
        claims = replace(
            self.claims,
            asserted_roles=frozenset({"provider", "institution_auditor"}),
        )
        actor = self.factory().build(claims, now=NOW)
        self.assertEqual(actor.audit_scope, "institution")

    def test_expired_token_is_rejected(self) -> None:
        self.assert_denied(
            replace(self.claims, expires_at=NOW),
            "identity_token_expired",
        )

    def test_stale_authentication_requires_reauthentication(self) -> None:
        self.assert_denied(
            replace(self.claims, authenticated_at=NOW - timedelta(hours=3)),
            "identity_reauthentication_required",
        )

    def test_missing_mfa_is_rejected(self) -> None:
        self.assert_denied(
            replace(self.claims, mfa_verified=False),
            "mfa_required",
        )

    def test_revoked_token_is_rejected(self) -> None:
        directory = Directory(
            self.authorization,
            revoked=frozenset({self.claims.token_id}),
        )
        self.assert_denied(
            self.claims,
            "identity_token_revoked",
            directory=directory,
        )

    def test_cross_institution_authorization_is_rejected(self) -> None:
        directory = Directory(
            replace(self.authorization, institution_id="INST-OTHER01")
        )
        self.assert_denied(
            self.claims,
            "authorization_scope_mismatch",
            directory=directory,
        )

    def test_unshared_roles_are_rejected(self) -> None:
        claims = replace(
            self.claims,
            asserted_roles=frozenset({"clinical_reviewer"}),
        )
        self.assert_denied(claims, "no_effective_role")

    def test_inactive_provider_is_rejected(self) -> None:
        directory = Directory(replace(self.authorization, active=False))
        self.assert_denied(
            self.claims,
            "inactive_provider",
            directory=directory,
        )


if __name__ == "__main__":
    unittest.main()
