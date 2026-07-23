"""Fail-closed access checks for assessment administration.

This module determines whether a user may start a specific assessment session.
It does not determine clinical appropriateness by itself; an approved pathway
and assessment plan remain mandatory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping


@dataclass(frozen=True)
class ProviderCredential:
    provider_id: str
    institution_id: str
    roles: frozenset[str]
    active: bool
    professional_license_expires: date | None
    authorized_tool_ids: frozenset[str] = field(default_factory=frozenset)
    completed_training_ids: frozenset[str] = field(default_factory=frozenset)
    languages: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class InstitutionAuthorization:
    institution_id: str
    active: bool
    approved_tool_ids: frozenset[str]
    data_processing_agreement_active: bool
    clinical_governance_active: bool


@dataclass(frozen=True)
class CaseAccessContext:
    case_id: str
    institution_id: str
    age_months: int
    assessment_language: str
    country_code: str
    approved_plan_tool_ids: frozenset[str]
    consent_scopes: frozenset[str]
    safety_level: str


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    assessment_id: str
    provider_id: str
    case_id: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()


_ALLOWED_DIGITAL_STATES = {
    "allowed",
    "allowed_after_governance_approval",
    "results_import_only",
}

_BLOCKED_LICENSE_STATES = {
    "unknown",
    "commercial_restricted",
    "commercial_or_permission_required",
    "tool_specific_permission_required",
    "electronic_license_review_required",
    "commercial_restricted_and_training_required",
}


def evaluate_assessment_access(
    *,
    catalog_entry: Mapping[str, Any],
    provider: ProviderCredential,
    institution: InstitutionAuthorization,
    case: CaseAccessContext,
    today: date | None = None,
    mode: str = "administration",
) -> AccessDecision:
    """Return a fail-closed decision for one requested assessment operation.

    `mode` is either ``administration`` or ``results_import``. Import-only
    integrations can never be used to display protected items or calculate
    publisher scores unless separately authorized.
    """

    current_date = today or date.today()
    reasons: list[str] = []
    warnings: list[str] = []

    assessment_id = _text(catalog_entry.get("id"), "catalog entry id")
    if mode not in {"administration", "results_import"}:
        reasons.append("unsupported_operation_mode")

    if not provider.active:
        reasons.append("provider_account_inactive")
    if provider.professional_license_expires is None:
        reasons.append("professional_license_expiry_missing")
    elif provider.professional_license_expires < current_date:
        reasons.append("professional_license_expired")

    if not institution.active:
        reasons.append("institution_inactive")
    if not institution.data_processing_agreement_active:
        reasons.append("institution_data_agreement_inactive")
    if not institution.clinical_governance_active:
        reasons.append("institution_clinical_governance_inactive")

    if provider.institution_id != institution.institution_id:
        reasons.append("provider_institution_mismatch")
    if case.institution_id != institution.institution_id:
        reasons.append("case_institution_mismatch")

    if assessment_id not in case.approved_plan_tool_ids:
        reasons.append("assessment_not_in_approved_case_plan")
    if "assessment" not in case.consent_scopes:
        reasons.append("assessment_consent_scope_missing")
    if case.safety_level in {"urgent", "emergency"}:
        reasons.append("routine_assessment_blocked_by_safety_level")

    enabled = catalog_entry.get("enabled") is True
    if not enabled:
        reasons.append("catalog_entry_disabled")

    blockers = catalog_entry.get("enablement_blockers", [])
    if not isinstance(blockers, list):
        reasons.append("invalid_catalog_blocker_configuration")
    elif blockers:
        reasons.append("catalog_entry_has_unresolved_blockers")

    license_status = catalog_entry.get("license_status")
    if not isinstance(license_status, str) or not license_status:
        reasons.append("license_status_missing")
    elif license_status in _BLOCKED_LICENSE_STATES:
        reasons.append("license_status_not_cleared")

    digital_status = catalog_entry.get("digital_right_status")
    if digital_status not in _ALLOWED_DIGITAL_STATES:
        reasons.append("digital_right_not_cleared")
    elif digital_status == "results_import_only" and mode != "results_import":
        reasons.append("assessment_is_results_import_only")

    if assessment_id not in provider.authorized_tool_ids:
        reasons.append("provider_not_authorized_for_tool")
    if assessment_id not in institution.approved_tool_ids:
        reasons.append("institution_not_authorized_for_tool")

    qualified_roles = catalog_entry.get("qualified_roles", [])
    if not isinstance(qualified_roles, list) or not qualified_roles:
        reasons.append("qualified_roles_missing")
    elif not provider.roles.intersection(qualified_roles):
        reasons.append("provider_role_not_qualified")

    required_training_ids = catalog_entry.get("required_training_ids", [])
    if not isinstance(required_training_ids, list):
        reasons.append("required_training_configuration_invalid")
    else:
        missing_training = sorted(set(required_training_ids) - provider.completed_training_ids)
        if missing_training:
            reasons.append("required_training_incomplete")
            warnings.append("missing_training:" + ",".join(missing_training))

    allowed_languages = catalog_entry.get("languages", [])
    if not isinstance(allowed_languages, list) or not allowed_languages:
        reasons.append("assessment_languages_missing")
    elif (
        "publisher_authorized_versions_only" not in allowed_languages
        and case.assessment_language not in allowed_languages
    ):
        reasons.append("assessment_language_not_supported")
    if case.assessment_language not in provider.languages:
        reasons.append("provider_language_competence_not_verified")

    age_min = catalog_entry.get("age_min_months")
    age_max = catalog_entry.get("age_max_months")
    if age_min is not None or age_max is not None:
        if not isinstance(age_min, int) or not isinstance(age_max, int):
            reasons.append("catalog_age_range_invalid")
        elif not age_min <= case.age_months <= age_max:
            reasons.append("case_age_outside_tool_range")
    else:
        warnings.append("tool_age_range_requires_specific_definition")

    country_codes = catalog_entry.get("approved_country_codes")
    if country_codes is not None:
        if not isinstance(country_codes, list) or not country_codes:
            reasons.append("approved_country_configuration_invalid")
        elif case.country_code not in country_codes:
            reasons.append("tool_not_approved_for_service_country")
    else:
        warnings.append("country_approval_requires_specific_definition")

    unique_reasons = tuple(dict.fromkeys(reasons))
    return AccessDecision(
        allowed=not unique_reasons,
        assessment_id=assessment_id,
        provider_id=provider.provider_id,
        case_id=case.case_id,
        reasons=unique_reasons,
        warnings=tuple(dict.fromkeys(warnings)),
    )


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
