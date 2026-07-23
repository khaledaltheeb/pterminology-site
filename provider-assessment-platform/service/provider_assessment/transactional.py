"""Atomic facade for compound provider-assessment application workflows."""

from __future__ import annotations

import re
from contextlib import AbstractContextManager
from datetime import date
from typing import Any, Protocol, Sequence

from .application import ProviderAssessmentService as BaseProviderAssessmentService
from .domain import (
    ActorContext,
    CaseRecord,
    CaseStatus,
    ConsentSnapshot,
    SafetyEvent,
    SafetyLevel,
)


_COUNTRY = re.compile(r"^[A-Z]{2}$")
_ALLOWED_REFERRAL_URGENCY = frozenset({"routine", "priority", "urgent"})


class AtomicRepository(Protocol):
    def atomic(
        self,
        *,
        actor: ActorContext | None = None,
    ) -> AbstractContextManager[None]: ...


class ProviderAssessmentService(BaseProviderAssessmentService):
    """Fail-closed service whose public writes commit or roll back as one unit.

    The base service contains the common workflow rules. This facade supplies
    the transaction boundary and the cross-layer intake contract used by the
    active OpenAPI and PostgreSQL drafts.
    """

    def __init__(self, repository: AtomicRepository, **kwargs: Any) -> None:
        if not callable(getattr(repository, "atomic", None)):
            raise TypeError(
                "ProviderAssessmentService requires a repository with an atomic() transaction boundary"
            )
        super().__init__(repository, **kwargs)

    def create_case(
        self,
        *,
        actor: ActorContext,
        identity_vault_reference: str,
        date_of_birth: date,
        age_months_at_intake: int,
        preferred_language: str,
        home_languages: Sequence[str],
        education_languages: Sequence[str],
        communication_modes: Sequence[str],
        country_of_service: str,
        referral_reason: str,
        referral_questions: Sequence[str],
        referrer_role: str,
        referral_urgency: str,
        consent: ConsentSnapshot,
        initial_safety_level: SafetyLevel,
        initial_safety_actions: Sequence[str],
        correlation_id: str,
    ) -> CaseRecord:
        with self._repository.atomic(actor=actor), self._operation_lock:
            self._require_active_actor(actor)
            self._require_role(
                actor,
                "intake_coordinator",
                "case_lead",
                "clinical_reviewer",
            )
            self._require_correlation_id(correlation_id)
            self._validate_opaque_reference(
                identity_vault_reference,
                "identity_vault_reference",
            )
            self._validate_opaque_reference(
                consent.document_reference,
                "consent.document_reference",
            )

            today = self._clock().date()
            self._require(
                date_of_birth <= today,
                "invalid_date_of_birth",
                "Date of birth cannot be in the future.",
            )
            calculated_age = self._completed_months(date_of_birth, today)
            self._require(
                0 <= age_months_at_intake <= 1440,
                "invalid_age",
                "Age at intake is outside the supported storage range.",
            )
            self._require(
                abs(calculated_age - age_months_at_intake) <= 1,
                "age_date_mismatch",
                "Age in months is inconsistent with date of birth and intake date.",
            )

            self._require(
                len(preferred_language.strip()) >= 2,
                "invalid_language",
                "Preferred language is required.",
            )
            home = self._clean_unique(
                home_languages,
                "home_languages",
                allow_empty=True,
            )
            education = self._clean_unique(
                education_languages,
                "education_languages",
                allow_empty=True,
            )
            modes = self._clean_unique(
                communication_modes,
                "communication_modes",
            )
            self._require(
                bool(modes),
                "communication_modes_required",
                "At least one communication mode is required.",
            )
            self._require(
                bool(_COUNTRY.fullmatch(country_of_service)),
                "invalid_country",
                "Country of service must be an ISO alpha-2 code.",
            )
            self._require(
                len(referral_reason.strip()) >= 10,
                "referral_reason_too_short",
                "A specific referral reason is required.",
            )
            questions = self._clean_unique(
                referral_questions,
                "referral_questions",
            )
            self._require(
                bool(questions),
                "referral_questions_required",
                "At least one answerable referral question is required.",
            )
            self._require(
                len(referrer_role.strip()) >= 2,
                "referrer_role_required",
                "Referrer role is required.",
            )
            self._require(
                referral_urgency in _ALLOWED_REFERRAL_URGENCY,
                "invalid_referral_urgency",
                "Referral urgency is not supported.",
            )
            self._require(
                consent.withdrawal_explained,
                "invalid_consent",
                "Consent must document that withdrawal was explained.",
            )
            self._require(
                consent.is_active_for("case_intake"),
                "consent_scope_missing",
                "Active consent does not include case intake.",
            )

            safety_actions = self._clean_unique(
                initial_safety_actions,
                "initial_safety_actions",
            )
            self._require(
                bool(safety_actions),
                "safety_actions_required",
                "The intake safety screen must document its action or no-action decision.",
            )
            if initial_safety_level in {
                SafetyLevel.URGENT,
                SafetyLevel.EMERGENCY,
            }:
                status = CaseStatus.SAFETY_HOLD
            else:
                status = CaseStatus.INTAKE

            now = self._clock()
            case_id = self._new_id("CASE")
            case = CaseRecord(
                case_id=case_id,
                institution_id=actor.institution_id,
                identity_vault_reference=identity_vault_reference,
                version=1,
                status=status,
                date_of_birth=date_of_birth,
                age_months_at_intake=age_months_at_intake,
                preferred_language=preferred_language.strip(),
                home_languages=home,
                education_languages=education,
                communication_modes=modes,
                country_of_service=country_of_service,
                referral_reason=referral_reason.strip(),
                referral_questions=questions,
                referrer_role=referrer_role.strip(),
                referral_urgency=referral_urgency,
                consent=consent,
                intake_safety_actions=safety_actions,
                safety_screened_at=now,
                safety_screened_by=actor.provider_id,
                safety_level=initial_safety_level,
                created_by_provider_id=actor.provider_id,
                assigned_case_lead_provider_id=(
                    actor.provider_id
                    if actor.has_role("case_lead", "clinical_reviewer")
                    else None
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
                    "home_language_count": str(len(home)),
                    "education_language_count": str(len(education)),
                    "referral_urgency": referral_urgency,
                },
            )

            if initial_safety_level in {
                SafetyLevel.MONITOR,
                SafetyLevel.URGENT,
                SafetyLevel.EMERGENCY,
            }:
                event = SafetyEvent(
                    safety_event_id=self._new_id("SAFE"),
                    case_id=case_id,
                    institution_id=actor.institution_id,
                    level=initial_safety_level,
                    domains=("intake",),
                    observations=(
                        "Safety concern documented during governed intake."
                    ),
                    immediate_actions=safety_actions,
                    handoff_target=None,
                    routine_pathway_blocked=(
                        initial_safety_level
                        in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY}
                    ),
                    created_by_provider_id=actor.provider_id,
                    created_at=now,
                )
                self._repository.append_safety_event(event)
            return case

    def record_safety_event(self, **kwargs: Any):
        with self._repository.atomic(actor=kwargs.get("actor")):
            return super().record_safety_event(**kwargs)

    def create_team_review_version(self, **kwargs: Any):
        with self._repository.atomic(actor=kwargs.get("actor")):
            return super().create_team_review_version(**kwargs)

    def create_report_draft(self, **kwargs: Any):
        with self._repository.atomic(actor=kwargs.get("actor")):
            return super().create_report_draft(**kwargs)

    def sign_report(self, **kwargs: Any):
        with self._repository.atomic(actor=kwargs.get("actor")):
            return super().sign_report(**kwargs)

    @staticmethod
    def _completed_months(born: date, on_date: date) -> int:
        months = (on_date.year - born.year) * 12 + (on_date.month - born.month)
        if on_date.day < born.day:
            months -= 1
        return months
