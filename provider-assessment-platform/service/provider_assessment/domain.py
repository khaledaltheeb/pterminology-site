"""Immutable domain models for governed provider assessment workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping, Sequence


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def immutable_mapping(value: Mapping[str, str] | None = None) -> Mapping[str, str]:
    return MappingProxyType(dict(value or {}))


class CaseStatus(StrEnum):
    INTAKE = "intake"
    SAFETY_HOLD = "safety_hold"
    ASSESSMENT_PLANNING = "assessment_planning"
    IN_ASSESSMENT = "in_assessment"
    MULTIDISCIPLINARY_REVIEW = "multidisciplinary_review"
    REPORT_DRAFT = "report_draft"
    APPROVED = "approved"
    CLOSED = "closed"
    WITHDRAWN = "withdrawn"


class SafetyLevel(StrEnum):
    NONE_IDENTIFIED = "none_identified"
    MONITOR = "monitor"
    URGENT = "urgent"
    EMERGENCY = "emergency"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    RETURNED_FOR_DATA = "returned_for_data"


class ReportStatus(StrEnum):
    DRAFT = "draft"
    SIGNED = "signed"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


@dataclass(frozen=True, slots=True)
class ActorContext:
    provider_id: str
    institution_id: str
    roles: frozenset[str]
    active: bool
    professional_license_verified: bool
    professional_license_reference: str
    assigned_case_ids: frozenset[str] = field(default_factory=frozenset)
    audit_scope: str | None = None

    def has_role(self, *roles: str) -> bool:
        return bool(self.roles.intersection(roles))

    def can_access_case(self, case_id: str) -> bool:
        return case_id in self.assigned_case_ids or self.audit_scope == "institution"


@dataclass(frozen=True, slots=True)
class ConsentSnapshot:
    consent_version_id: str
    legal_basis: str
    scope: frozenset[str]
    obtained_at: datetime
    withdrawal_explained: bool
    document_reference: str = ""
    withdrawn_at: datetime | None = None

    def is_active_for(self, operation: str) -> bool:
        return self.withdrawn_at is None and operation in self.scope


@dataclass(frozen=True, slots=True)
class CaseRecord:
    case_id: str
    institution_id: str
    identity_vault_reference: str
    version: int
    status: CaseStatus
    age_months_at_intake: int
    preferred_language: str
    communication_modes: tuple[str, ...]
    country_of_service: str
    referral_reason: str
    referral_questions: tuple[str, ...]
    consent: ConsentSnapshot
    date_of_birth: date | None = None
    home_languages: tuple[str, ...] = ()
    education_languages: tuple[str, ...] = ()
    referrer_role: str = ""
    referral_urgency: str = "routine"
    intake_safety_actions: tuple[str, ...] = ()
    safety_screened_at: datetime | None = None
    safety_screened_by: str = ""
    safety_level: SafetyLevel = SafetyLevel.NONE_IDENTIFIED
    current_pathway_id: str | None = None
    current_pathway_version: str | None = None
    created_by_provider_id: str = ""
    assigned_case_lead_provider_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class SafetyEvent:
    safety_event_id: str
    case_id: str
    institution_id: str
    level: SafetyLevel
    domains: tuple[str, ...]
    observations: str
    immediate_actions: tuple[str, ...]
    handoff_target: str | None
    routine_pathway_blocked: bool
    created_by_provider_id: str
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class TeamReviewVersion:
    team_review_id: str
    review_group_id: str
    case_id: str
    institution_id: str
    pathway_instance_id: str
    version: int
    status: ReviewStatus
    member_provider_ids: tuple[str, ...]
    decision: str
    supporting_evidence_ids: tuple[str, ...]
    contrary_evidence_ids: tuple[str, ...]
    limitations: str
    support_needs: tuple[str, ...]
    created_by_provider_id: str
    approved_by_provider_id: str | None = None
    approved_at: datetime | None = None
    supersedes_team_review_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ReportVersion:
    report_version_id: str
    report_id: str
    case_id: str
    institution_id: str
    team_review_id: str
    version: int
    status: ReportStatus
    template_version: str
    content_reference: str
    content_hash: str
    created_by_provider_id: str
    human_review_required: bool = True
    signed_by_provider_id: str | None = None
    professional_license_reference: str | None = None
    signed_at: datetime | None = None
    supersedes_report_version_id: str | None = None
    withdrawal_reason: str | None = None
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    audit_event_id: str
    institution_id: str
    actor_provider_id: str
    action: str
    object_type: str
    object_id: str
    reason: str
    correlation_id: str
    case_id: str | None
    previous_event_hash: str | None
    event_hash: str
    metadata: Mapping[str, str] = field(default_factory=immutable_mapping)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class ReviewInput:
    review_group_id: str
    pathway_instance_id: str
    status: ReviewStatus
    member_provider_ids: Sequence[str]
    decision: str
    supporting_evidence_ids: Sequence[str]
    contrary_evidence_ids: Sequence[str]
    limitations: str
    support_needs: Sequence[str]
    supersedes_team_review_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReportDraftInput:
    report_id: str
    template_version: str
    content_reference: str
    content_hash: str
    supersedes_report_version_id: str | None = None
