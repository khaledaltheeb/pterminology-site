"""Verified identity boundary for constructing provider actor contexts.

Network adapters must never construct ``ActorContext`` directly from arbitrary
request fields. They must validate the identity-provider token and intersect its
claims with current institutional authorization data through this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from .domain import ActorContext
from .errors import PermissionDenied, ValidationError


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValidationError(
            "timezone_required",
            "Identity timestamps must be timezone-aware.",
        )
    return value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class VerifiedIdentityClaims:
    token_id: str
    issuer: str
    audience: str
    subject_reference: str
    provider_id: str
    institution_id: str
    asserted_roles: frozenset[str]
    authenticated_at: datetime
    expires_at: datetime
    mfa_verified: bool


@dataclass(frozen=True, slots=True)
class ProviderAuthorizationSnapshot:
    provider_id: str
    institution_id: str
    active: bool
    authorized_roles: frozenset[str]
    professional_license_verified: bool
    professional_license_reference: str
    assigned_case_ids: frozenset[str]
    audit_scope: str | None = None


class AuthorizationDirectory(Protocol):
    def get_provider_authorization(
        self,
        provider_id: str,
        institution_id: str,
    ) -> ProviderAuthorizationSnapshot: ...

    def is_token_revoked(self, token_id: str) -> bool: ...


class ActorContextFactory:
    """Build an actor context only after identity and authorization convergence."""

    def __init__(
        self,
        directory: AuthorizationDirectory,
        *,
        trusted_issuer: str,
        expected_audience: str,
        maximum_authentication_age: timedelta = timedelta(hours=12),
    ) -> None:
        if not trusted_issuer.strip() or not expected_audience.strip():
            raise ValueError("Trusted issuer and audience are required")
        if maximum_authentication_age <= timedelta(0):
            raise ValueError("Maximum authentication age must be positive")
        self._directory = directory
        self._trusted_issuer = trusted_issuer
        self._expected_audience = expected_audience
        self._maximum_authentication_age = maximum_authentication_age

    def build(
        self,
        claims: VerifiedIdentityClaims,
        *,
        now: datetime,
    ) -> ActorContext:
        current = _utc(now)
        authenticated = _utc(claims.authenticated_at)
        expires = _utc(claims.expires_at)

        self._require(
            claims.issuer == self._trusted_issuer,
            "untrusted_identity_issuer",
            "The identity token issuer is not trusted.",
        )
        self._require(
            claims.audience == self._expected_audience,
            "invalid_identity_audience",
            "The identity token was not issued for this service.",
        )
        self._require(
            bool(claims.token_id.strip() and claims.subject_reference.strip()),
            "incomplete_identity_claims",
            "Token and subject references are required.",
        )
        self._require(
            expires > current,
            "identity_token_expired",
            "The identity token has expired.",
        )
        self._require(
            authenticated <= current,
            "identity_authentication_in_future",
            "The authentication time is in the future.",
        )
        self._require(
            current - authenticated <= self._maximum_authentication_age,
            "identity_reauthentication_required",
            "The authentication is too old for sensitive assessment operations.",
        )
        self._require(
            claims.mfa_verified,
            "mfa_required",
            "Multi-factor authentication is required.",
        )
        self._require(
            not self._directory.is_token_revoked(claims.token_id),
            "identity_token_revoked",
            "The identity token has been revoked.",
        )

        authorization = self._directory.get_provider_authorization(
            claims.provider_id,
            claims.institution_id,
        )
        self._require(
            authorization.provider_id == claims.provider_id
            and authorization.institution_id == claims.institution_id,
            "authorization_scope_mismatch",
            "Identity and institutional authorization scopes do not match.",
        )
        self._require(
            authorization.active,
            "inactive_provider",
            "The provider is not active in the institution.",
        )

        effective_roles = claims.asserted_roles.intersection(
            authorization.authorized_roles
        )
        self._require(
            bool(effective_roles),
            "no_effective_role",
            "No currently authorized role is shared by the token and institution.",
        )

        audit_scope = None
        if (
            authorization.audit_scope == "institution"
            and "institution_auditor" in effective_roles
        ):
            audit_scope = "institution"

        return ActorContext(
            provider_id=authorization.provider_id,
            institution_id=authorization.institution_id,
            roles=frozenset(effective_roles),
            active=authorization.active,
            professional_license_verified=(
                authorization.professional_license_verified
            ),
            professional_license_reference=(
                authorization.professional_license_reference
            ),
            assigned_case_ids=authorization.assigned_case_ids,
            audit_scope=audit_scope,
        )

    @staticmethod
    def _require(condition: bool, code: str, message: str) -> None:
        if not condition:
            raise PermissionDenied(code, message)
