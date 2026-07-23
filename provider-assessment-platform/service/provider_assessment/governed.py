"""Final governed service facade with database-consistent safety sequencing."""

from __future__ import annotations

from dataclasses import replace
from typing import Sequence

from .domain import ActorContext, CaseRecord, CaseStatus, SafetyEvent, SafetyLevel
from .errors import ConflictError
from .transactional import ProviderAssessmentService as AtomicProviderAssessmentService


class ProviderAssessmentService(AtomicProviderAssessmentService):
    """Public service facade used by adapters and tests.

    Safety state is saved with optimistic concurrency before the immutable event
    is appended. The complete operation remains inside one repository transaction,
    so event failure rolls the case update back. The database trigger remains a
    defense-in-depth path for direct event inserts and must be idempotent when the
    service already applied the target state.
    """

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
        with self._repository.atomic(actor=actor), self._operation_lock:
            case = self._authorized_case(
                actor,
                case_id,
                "provider",
                "case_lead",
                "clinical_reviewer",
            )
            self._require_correlation_id(correlation_id)
            self._require(
                level is not SafetyLevel.NONE_IDENTIFIED,
                "invalid_safety_event",
                "A safety event must have monitor, urgent, or emergency level.",
            )
            cleaned_domains = self._clean_unique(domains, "domains")
            actions = self._clean_unique(immediate_actions, "immediate_actions")
            self._require(
                bool(cleaned_domains),
                "safety_domains_required",
                "At least one safety domain is required.",
            )
            self._require(
                len(observations.strip()) >= 10,
                "safety_observations_required",
                "Specific safety observations are required.",
            )
            self._require(
                bool(actions),
                "safety_actions_required",
                "Immediate actions are required for a safety event.",
            )
            if level in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY}:
                self._require(
                    bool(handoff_target and handoff_target.strip()),
                    "safety_handoff_required",
                    "Urgent and emergency events require a handoff target.",
                )

            event = SafetyEvent(
                safety_event_id=self._new_id("SAFE"),
                case_id=case.case_id,
                institution_id=case.institution_id,
                level=level,
                domains=cleaned_domains,
                observations=observations.strip(),
                immediate_actions=actions,
                handoff_target=handoff_target.strip() if handoff_target else None,
                routine_pathway_blocked=level
                in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY},
                created_by_provider_id=actor.provider_id,
                created_at=self._clock(),
            )

            if level in {SafetyLevel.URGENT, SafetyLevel.EMERGENCY}:
                next_status = CaseStatus.SAFETY_HOLD
                next_level = level
            elif case.safety_level in {
                SafetyLevel.URGENT,
                SafetyLevel.EMERGENCY,
            }:
                # A lower-severity observation never clears or downgrades an
                # existing urgent hold. Resumption requires a separate reviewed
                # safety-event decision workflow.
                next_status = case.status
                next_level = case.safety_level
            else:
                next_status = case.status
                next_level = SafetyLevel.MONITOR

            state_changed = (
                next_status is not case.status
                or next_level is not case.safety_level
            )
            if state_changed:
                updated = replace(
                    case,
                    status=next_status,
                    safety_level=next_level,
                    updated_at=self._clock(),
                )
                saved = self._repository.save_case(
                    updated,
                    expected_version=expected_case_version,
                )
            else:
                if case.version != expected_case_version:
                    raise ConflictError(
                        "case_version_conflict",
                        "The case changed after it was read; reload before recording the safety event.",
                        {
                            "case_id": case.case_id,
                            "expected_version": expected_case_version,
                            "current_version": case.version,
                        },
                    )
                saved = case

            self._repository.append_safety_event(event)
            self._audit(
                actor=actor,
                action="safety_event.create",
                object_type="safety_event",
                object_id=event.safety_event_id,
                reason="Record and route a governed safety event",
                correlation_id=correlation_id,
                case_id=case.case_id,
                metadata={
                    "event_level": level.value,
                    "case_safety_level": saved.safety_level.value,
                    "case_version_changed": str(state_changed).lower(),
                    "routine_pathway_blocked": str(
                        event.routine_pathway_blocked
                    ).lower(),
                },
            )
            return saved, event
