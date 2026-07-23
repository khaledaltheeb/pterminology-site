"""Deterministic application workflows for the provider assessment platform.

The service operates on opaque references and structured governance metadata.
It does not calculate proprietary test scores, expose protected assessment
content, or create automatic diagnoses or eligibility decisions.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import replace
from datetime import datetime
from threading import RLock
from typing import Callable, Iterable, Mapping, Sequence

from .audit import build_audit_event
from .domain import (
    ActorContext,
    CaseRecord,
    CaseStatus,
    ConsentSnapshot,
    ReportDraftInput,
    ReportStatus,
    ReportVersion,
    ReviewInput,
    ReviewStatus,
    SafetyEvent,
    SafetyLevel,
    TeamReviewVersion,
    utc_now,
)
from .errors import ConflictError, PermissionDenied, ValidationError
from .repository import Repository

_ID_COMPONENT = re.compile(r"^[A-Z0-9-]{6,50}$")
_HASH = re.compile(r"^[a-f0-9]{64}$")
_COUNTRY = re.compile(r"^[A-Z]{2}$")
_OPAQUE_REFERENCE = re.compile(r"^[A-Z][A-Z0-9:_./-]{5,250}$")


def default_id_factory(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(8).upper()}"


class ProviderAssessmentService:
    """Application service with fail-closed professional workflow gates."""

    def __init__(
        self,
        repository: Repository,
        *,
        id_factory: Callable[[str], str] = default_id_factory,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repository = repository
        self._id_factory = id_factory
        self._clock = clock
        self._operation_lock = RLock()

    def create_case(
        self,
        *,
        actor: ActorContext,
        identity_vault_reference: str,
        age_months_at_intake: int,
        preferred_language: str,
        communication_modes: Sequence[str],
        country_of_service: str,
        referral_reason: str,
        referral_questions: Sequence[str],
        consent: ConsentSnapshot,
        initial_safety_level: SafetyLevel,
        initial_safety_actions: Sequence[str],
        correlation_id: str,
    ) -> CaseRecord:
        with self._operation_lock:
            self._require_active_actor(actor)
            self._require_role(actor, "intake_coordinator", "case_lead", "clinical_reviewer")
            self._require_correlation_id(correlation_id)
            self._validate_opaque_reference(identity_vault_reference, "identity_vault_reference")
            self._require(0 <= age_months_at_intake <= 1440, "invalid_age", "Age at intake is outside the supported storage range.")
            self._require(len(preferred_language.strip()) >= 2, "invalid_language", "Preferred language is required.")
            modes = self._clean_unique(communication_modes, "communication_modes")
            self._require(bool(modes), "communication_modes_required", "At least one communication mode is required.")
            self._require(bool(_COUNTRY.fullmatch(country_of_service)), "invalid_country", "Country of service must be an ISO alpha-2 code.")
            self._require(len(referral_reason.strip()) >= 10, "referral_reason_too_short", "A specific referral reason is required.")
            questions = self._clean_unique(referral_questions, "referral_questions")
            self._require(bool(questions), "referral_questions_required", "At least one answerable referral question is required.")
            self._require(consent.withdrawal_explained, "invalid_consent", "Consent must document that withdrawal was explained.")
            self._require(consent.is_active_for("case_intake"), "consent_scope_missing", "Active consent does not include case intake.")

            safety_actions = self._clean_unique(initial_safety_actions, "initial_safety_actions", allow_empty=True)
            if initial_safety_level in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY}:
                self._require(bool(safety_actions), "urgent_actions_required", "Urgent or emergency intake requires documented immediate actions.")
                status = CaseStatus.SAFETY_HOLD
            else:
                status = CaseStatus.INTAKE

            now = self._clock()
            case_id = self._id_factory("CASE")
            self._validate_generated_id(case_id, "CASE")
            case = CaseRecord(
                case_id=case_id,
                institution_id=actor.institution_id,
                identity_vault_reference=identity_vault_reference,
                version=1,
                status=status,
                age_months_at_intake=age_months_at_intake,
                preferred_language=preferred_language.strip(),
                communication_modes=modes,
                country_of_service=country_of_service,
                referral_reason=referral_reason.strip(),
                referral_questions=questions,
                consent=consent,
                safety_level=initial_safety_level,
                created_by_provider_id=actor.provider_id,
                assigned_case_lead_provider_id=(
                    actor.provider_id if actor.has_role("case_lead", "clinical_reviewer") else None
                ),
                created_at=now,
                updated_at=now,
            )
            self._repository.add_case(case)
            self._audit(
                actor=actor,
                action="case.create",
                object_type="case",
                object_id=case_id,
                reason="Create governed case intake",
                correlation_id=correlation_id,
                case_id=case_id,
                metadata={
                    "status": status.value,
                    "safety_level": initial_safety_level.value,
                },
            )

            if initial_safety_level in {SafetyLevel.MONITOR, SafetyLevel.URGENT, SafetyLevel.EMERGENCY}:
                event = SafetyEvent(
                    safety_event_id=self._new_id("SAFE"),
                    case_id=case_id,
                    institution_id=actor.institution_id,
                    level=initial_safety_level,
                    domains=("intake",),
                    observations="Safety concern documented during governed intake.",
                    immediate_actions=safety_actions or ("monitor_and_review",),
                    handoff_target=None,
                    routine_pathway_blocked=initial_safety_level in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY},
                    created_by_provider_id=actor.provider_id,
                    created_at=now,
                )
                self._repository.append_safety_event(event)
            return case

    def record_safety_event(
        self,
        *,
        actor: ActorContext,
        case_id: str,
        expected_case_version: int,
        level: SafetyLevel,
        domains: Sequence[str],
        observations: str,
        immediate_actions: Sequence[str],
        handoff_target: str | None,
        correlation_id: str,
    ) -> tuple[CaseRecord, SafetyEvent]:
        with self._operation_lock:
            case = self._authorized_case(actor, case_id, "provider", "case_lead", "clinical_reviewer")
            self._require_correlation_id(correlation_id)
            self._require(level is not SafetyLevel.NONE_IDENTIFIED, "invalid_safety_event", "A safety event must have monitor, urgent, or emergency level.")
            cleaned_domains = self._clean_unique(domains, "domains")
            actions = self._clean_unique(immediate_actions, "immediate_actions")
            self._require(bool(cleaned_domains), "safety_domains_required", "At least one safety domain is required.")
            self._require(len(observations.strip()) >= 10, "safety_observations_required", "Specific safety observations are required.")
            self._require(bool(actions), "safety_actions_required", "Immediate actions are required for a safety event.")
            if level in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY}:
                self._require(bool(handoff_target and handoff_target.strip()), "safety_handoff_required", "Urgent and emergency events require a handoff target.")

            event = SafetyEvent(
                safety_event_id=self._new_id("SAFE"),
                case_id=case.case_id,
                institution_id=case.institution_id,
                level=level,
                domains=cleaned_domains,
                observations=observations.strip(),
                immediate_actions=actions,
                handoff_target=handoff_target.strip() if handoff_target else None,
                routine_pathway_blocked=level in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY},
                created_by_provider_id=actor.provider_id,
                created_at=self._clock(),
            )
            self._repository.append_safety_event(event)

            next_status = (
                CaseStatus.SAFETY_HOLD
                if level in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY}
                else case.status
            )
            updated = replace(
                case,
                status=next_status,
                safety_level=level,
                updated_at=self._clock(),
            )
            saved = self._repository.save_case(updated, expected_version=expected_case_version)
            self._audit(
                actor=actor,
                action="safety_event.create",
                object_type="safety_event",
                object_id=event.safety_event_id,
                reason="Record and route a governed safety event",
                correlation_id=correlation_id,
                case_id=case.case_id,
                metadata={
                    "level": level.value,
                    "routine_pathway_blocked": str(event.routine_pathway_blocked).lower(),
                },
            )
            return saved, event

    def create_team_review_version(
        self,
        *,
        actor: ActorContext,
        case_id: str,
        review_input: ReviewInput,
        correlation_id: str,
    ) -> TeamReviewVersion:
        with self._operation_lock:
            case = self._authorized_case(actor, case_id, "case_lead", "clinical_reviewer")
            self._require_licensed_actor(actor)
            self._require_correlation_id(correlation_id)
            self._require(case.status is not CaseStatus.SAFETY_HOLD, "case_on_safety_hold", "Team review is blocked while an urgent safety hold is active.")
            self._require(case.consent.is_active_for("multidisciplinary_review"), "consent_scope_missing", "Active consent does not include multidisciplinary review.")
            self._validate_opaque_reference(review_input.pathway_instance_id, "pathway_instance_id")
            self._validate_opaque_reference(review_input.review_group_id, "review_group_id")

            members = self._clean_unique(review_input.member_provider_ids, "member_provider_ids")
            supporting = self._clean_unique(review_input.supporting_evidence_ids, "supporting_evidence_ids", allow_empty=True)
            contrary = self._clean_unique(review_input.contrary_evidence_ids, "contrary_evidence_ids", allow_empty=True)
            needs = self._clean_unique(review_input.support_needs, "support_needs", allow_empty=True)
            self._require(len(review_input.decision.strip()) >= 10, "review_decision_required", "A specific review decision is required.")
            self._require(len(review_input.limitations.strip()) >= 10, "review_limitations_required", "Review limitations must be explicit.")

            latest = self._repository.get_latest_team_review(
                review_input.review_group_id,
                actor.institution_id,
                case_id,
            )
            if latest is None:
                self._require(review_input.supersedes_team_review_id is None, "unexpected_supersedes", "The first review version cannot supersede another review.")
                version = 1
            else:
                self._require(
                    review_input.supersedes_team_review_id == latest.team_review_id,
                    "stale_review_version",
                    "A new review version must supersede the latest review version.",
                )
                self._require(
                    not (
                        latest.status is ReviewStatus.APPROVED
                        and review_input.status is ReviewStatus.DRAFT
                    ),
                    "approved_review_regression",
                    "An approved team review cannot be superseded by an unapproved draft.",
                )
                version = latest.version + 1

            approved_by: str | None = None
            approved_at: datetime | None = None
            if review_input.status is ReviewStatus.APPROVED:
                self._require(actor.has_role("clinical_reviewer"), "clinical_reviewer_required", "Only a clinical reviewer can approve a multidisciplinary review.")
                self._require(len(members) >= 2, "two_reviewers_required", "An approved review requires at least two distinct members.")
                self._require(len(supporting) >= 2, "multiple_evidence_sources_required", "An approved review requires at least two supporting evidence references.")
                self._require(actor.provider_id in members, "approver_must_be_member", "The approving reviewer must be listed as a team member.")
                approved_by = actor.provider_id
                approved_at = self._clock()

            review = TeamReviewVersion(
                team_review_id=self._new_id("TREV"),
                review_group_id=review_input.review_group_id,
                case_id=case.case_id,
                institution_id=case.institution_id,
                pathway_instance_id=review_input.pathway_instance_id,
                version=version,
                status=review_input.status,
                member_provider_ids=members,
                decision=review_input.decision.strip(),
                supporting_evidence_ids=supporting,
                contrary_evidence_ids=contrary,
                limitations=review_input.limitations.strip(),
                support_needs=needs,
                created_by_provider_id=actor.provider_id,
                approved_by_provider_id=approved_by,
                approved_at=approved_at,
                supersedes_team_review_id=review_input.supersedes_team_review_id,
                created_at=self._clock(),
            )
            self._repository.append_team_review(review)
            self._audit(
                actor=actor,
                action="team_review.append_version",
                object_type="team_review",
                object_id=review.team_review_id,
                reason="Append an immutable multidisciplinary review version",
                correlation_id=correlation_id,
                case_id=case.case_id,
                metadata={
                    "review_group_id": review.review_group_id,
                    "version": str(review.version),
                    "status": review.status.value,
                },
            )
            return review

    def create_report_draft(
        self,
        *,
        actor: ActorContext,
        case_id: str,
        team_review_id: str,
        draft_input: ReportDraftInput,
        expected_case_version: int,
        correlation_id: str,
    ) -> tuple[CaseRecord, ReportVersion]:
        with self._operation_lock:
            case = self._authorized_case(actor, case_id, "report_author", "case_lead", "clinical_reviewer")
            self._require_licensed_actor(actor)
            self._require_correlation_id(correlation_id)
            self._require(case.status is not CaseStatus.SAFETY_HOLD, "case_on_safety_hold", "Report creation is blocked while an urgent safety hold is active.")
            self._require(case.consent.is_active_for("professional_report"), "consent_scope_missing", "Active consent does not include professional reporting.")
            review = self._repository.get_team_review(team_review_id, actor.institution_id, case_id)
            self._require(review.status is ReviewStatus.APPROVED, "approved_review_required", "A report requires an approved multidisciplinary review.")
            latest_review = self._repository.get_latest_team_review(
                review.review_group_id,
                actor.institution_id,
                case_id,
            )
            self._require(
                latest_review is not None and latest_review.team_review_id == review.team_review_id,
                "latest_review_required",
                "A report must use the latest review version in the review group.",
            )
            self._validate_opaque_reference(draft_input.content_reference, "content_reference")
            self._require(bool(_HASH.fullmatch(draft_input.content_hash)), "invalid_content_hash", "Report content hash must be a lowercase SHA-256 digest.")
            self._require(len(draft_input.template_version.strip()) >= 1, "template_version_required", "Report template version is required.")
            self._validate_opaque_reference(draft_input.report_id, "report_id")

            latest_report = self._repository.get_latest_report(
                draft_input.report_id,
                actor.institution_id,
                case_id,
            )
            if latest_report is None:
                self._require(draft_input.supersedes_report_version_id is None, "unexpected_supersedes", "The first report version cannot supersede another report.")
                version = 1
            else:
                self._require(
                    draft_input.supersedes_report_version_id == latest_report.report_version_id,
                    "stale_report_version",
                    "A report version must supersede the latest version.",
                )
                self._require(
                    latest_report.status is not ReportStatus.SIGNED,
                    "signed_report_requires_correction_workflow",
                    "A signed report cannot be replaced by a draft through the standard drafting workflow.",
                )
                version = latest_report.version + 1

            report = ReportVersion(
                report_version_id=self._new_id("RPTV"),
                report_id=draft_input.report_id,
                case_id=case.case_id,
                institution_id=case.institution_id,
                team_review_id=review.team_review_id,
                version=version,
                status=ReportStatus.DRAFT,
                template_version=draft_input.template_version.strip(),
                content_reference=draft_input.content_reference,
                content_hash=draft_input.content_hash,
                created_by_provider_id=actor.provider_id,
                human_review_required=True,
                supersedes_report_version_id=draft_input.supersedes_report_version_id,
                created_at=self._clock(),
            )
            self._repository.append_report(report)
            updated = replace(
                case,
                status=CaseStatus.REPORT_DRAFT,
                updated_at=self._clock(),
            )
            saved_case = self._repository.save_case(updated, expected_version=expected_case_version)
            self._audit(
                actor=actor,
                action="report.create_draft",
                object_type="report_version",
                object_id=report.report_version_id,
                reason="Create an unsigned professional report draft from an approved review",
                correlation_id=correlation_id,
                case_id=case.case_id,
                metadata={
                    "report_id": report.report_id,
                    "version": str(report.version),
                    "team_review_id": report.team_review_id,
                },
            )
            return saved_case, report

    def sign_report(
        self,
        *,
        actor: ActorContext,
        case_id: str,
        draft_report_version_id: str,
        confirmed_content_hash: str,
        expected_case_version: int,
        attestation: str,
        correlation_id: str,
    ) -> tuple[CaseRecord, ReportVersion]:
        with self._operation_lock:
            case = self._authorized_case(actor, case_id, "clinical_reviewer")
            self._require_licensed_actor(actor)
            self._require_correlation_id(correlation_id)
            self._require(case.status is not CaseStatus.SAFETY_HOLD, "case_on_safety_hold", "Report signing is blocked while an urgent safety hold is active.")
            self._require(case.consent.is_active_for("professional_report"), "consent_scope_missing", "Active consent does not include professional reporting.")
            self._require(len(attestation.strip()) >= 20, "attestation_required", "A substantive signing attestation is required.")
            self._require(bool(_HASH.fullmatch(confirmed_content_hash)), "invalid_content_hash", "Confirmed content hash must be a lowercase SHA-256 digest.")

            draft = self._repository.get_report_version(
                draft_report_version_id,
                actor.institution_id,
                case_id,
            )
            self._require(draft.status is ReportStatus.DRAFT, "draft_report_required", "Only an unsigned draft can enter the signing workflow.")
            self._require(draft.content_hash == confirmed_content_hash, "report_hash_mismatch", "The reviewed content hash does not match the stored draft.")
            latest = self._repository.get_latest_report(draft.report_id, actor.institution_id, case_id)
            self._require(
                latest is not None and latest.report_version_id == draft.report_version_id,
                "latest_report_required",
                "Only the latest report version can be signed.",
            )
            review = self._repository.get_team_review(
                draft.team_review_id,
                actor.institution_id,
                case_id,
            )
            self._require(review.status is ReviewStatus.APPROVED, "approved_review_required", "The report no longer references an approved review.")

            signed = replace(
                draft,
                report_version_id=self._new_id("RPTV"),
                version=draft.version + 1,
                status=ReportStatus.SIGNED,
                signed_by_provider_id=actor.provider_id,
                professional_license_reference=actor.professional_license_reference,
                signed_at=self._clock(),
                supersedes_report_version_id=draft.report_version_id,
                created_by_provider_id=draft.created_by_provider_id,
                created_at=self._clock(),
            )
            self._repository.append_report(signed)
            updated = replace(
                case,
                status=CaseStatus.APPROVED,
                updated_at=self._clock(),
            )
            saved_case = self._repository.save_case(updated, expected_version=expected_case_version)
            self._audit(
                actor=actor,
                action="report.sign",
                object_type="report_version",
                object_id=signed.report_version_id,
                reason="Sign a reviewed professional report version",
                correlation_id=correlation_id,
                case_id=case.case_id,
                metadata={
                    "report_id": signed.report_id,
                    "version": str(signed.version),
                    "supersedes": draft.report_version_id,
                },
            )
            return saved_case, signed

    def _authorized_case(self, actor: ActorContext, case_id: str, *roles: str) -> CaseRecord:
        self._require_active_actor(actor)
        self._require_role(actor, *roles)
        self._require(actor.can_access_case(case_id), "case_access_denied", "The actor is not assigned to this case.", permission=True)
        return self._repository.get_case(case_id, actor.institution_id)

    def _require_active_actor(self, actor: ActorContext) -> None:
        self._require(actor.active, "inactive_actor", "The provider account is inactive.", permission=True)
        self._require(bool(actor.provider_id and actor.institution_id), "invalid_actor_context", "Provider and institution context are required.", permission=True)

    def _require_licensed_actor(self, actor: ActorContext) -> None:
        self._require(actor.professional_license_verified, "professional_license_required", "A current verified professional license is required.", permission=True)
        self._require(bool(actor.professional_license_reference.strip()), "professional_license_reference_required", "A professional license reference is required.", permission=True)

    def _require_role(self, actor: ActorContext, *roles: str) -> None:
        self._require(actor.has_role(*roles), "role_required", "The actor does not have a required role.", permission=True, details={"allowed_roles": ",".join(sorted(roles))})

    def _audit(
        self,
        *,
        actor: ActorContext,
        action: str,
        object_type: str,
        object_id: str,
        reason: str,
        correlation_id: str,
        case_id: str | None,
        metadata: Mapping[str, str],
    ) -> None:
        previous_hash = self._repository.last_audit_hash(actor.institution_id)
        event = build_audit_event(
            audit_event_id=self._new_id("AUD"),
            actor=actor,
            action=action,
            object_type=object_type,
            object_id=object_id,
            reason=reason,
            correlation_id=correlation_id,
            case_id=case_id,
            previous_event_hash=previous_hash,
            metadata=metadata,
            occurred_at=self._clock(),
        )
        self._repository.append_audit_event(event)

    def _new_id(self, prefix: str) -> str:
        value = self._id_factory(prefix)
        self._validate_generated_id(value, prefix)
        return value

    @staticmethod
    def _validate_generated_id(value: str, prefix: str) -> None:
        expected = f"{prefix}-"
        if not value.startswith(expected) or not _ID_COMPONENT.fullmatch(value[len(expected) :]):
            raise ValidationError(
                "invalid_generated_identifier",
                "The configured identifier factory produced an invalid identifier.",
                {"prefix": prefix},
            )

    @staticmethod
    def _validate_opaque_reference(value: str, field: str) -> None:
        if not _OPAQUE_REFERENCE.fullmatch(value):
            raise ValidationError(
                "invalid_opaque_reference",
                "The field must contain an opaque system reference, not direct identity or protected content.",
                {"field": field},
            )

    @staticmethod
    def _require_correlation_id(value: str) -> None:
        if len(value.strip()) < 8 or len(value) > 128:
            raise ValidationError(
                "invalid_correlation_id",
                "Correlation identifier length is invalid.",
                {"field": "correlation_id"},
            )

    @staticmethod
    def _clean_unique(
        values: Iterable[str],
        field: str,
        *,
        allow_empty: bool = False,
    ) -> tuple[str, ...]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = raw.strip()
            if not value:
                if allow_empty:
                    continue
                raise ValidationError(
                    "empty_collection_value",
                    "Collection values cannot be blank.",
                    {"field": field},
                )
            if value not in seen:
                seen.add(value)
                cleaned.append(value)
        return tuple(cleaned)

    @staticmethod
    def _require(
        condition: bool,
        code: str,
        message: str,
        *,
        permission: bool = False,
        details: Mapping[str, object] | None = None,
    ) -> None:
        if condition:
            return
        error_type = PermissionDenied if permission else ValidationError
        raise error_type(code, message, details)
