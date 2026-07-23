"""Repository ports and a test-only in-memory implementation.

The in-memory repository is for deterministic tests and interface development.
It must never be used for real-person or production data.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from threading import RLock
from typing import Protocol

from .domain import AuditEvent, CaseRecord, ReportVersion, SafetyEvent, TeamReviewVersion
from .errors import ConflictError, NotFoundError


class Repository(Protocol):
    def add_case(self, case: CaseRecord) -> None: ...

    def get_case(self, case_id: str, institution_id: str) -> CaseRecord: ...

    def save_case(self, case: CaseRecord, *, expected_version: int) -> CaseRecord: ...

    def append_safety_event(self, event: SafetyEvent) -> None: ...

    def append_team_review(self, review: TeamReviewVersion) -> None: ...

    def get_team_review(self, review_id: str, institution_id: str, case_id: str) -> TeamReviewVersion: ...

    def get_latest_team_review(
        self, review_group_id: str, institution_id: str, case_id: str
    ) -> TeamReviewVersion | None: ...

    def append_report(self, report: ReportVersion) -> None: ...

    def get_report_version(
        self, report_version_id: str, institution_id: str, case_id: str
    ) -> ReportVersion: ...

    def get_latest_report(
        self, report_id: str, institution_id: str, case_id: str
    ) -> ReportVersion | None: ...

    def append_audit_event(self, event: AuditEvent) -> None: ...

    def last_audit_hash(self, institution_id: str) -> str | None: ...


class InMemoryRepository:
    """Thread-safe repository used only by the isolated service tests."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._cases: dict[tuple[str, str], CaseRecord] = {}
        self._safety_events: dict[str, SafetyEvent] = {}
        self._reviews: dict[str, TeamReviewVersion] = {}
        self._review_groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        self._reports: dict[str, ReportVersion] = {}
        self._report_groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
        self._audit_events: list[AuditEvent] = []
        self._last_audit_hash: dict[str, str] = {}

    def add_case(self, case: CaseRecord) -> None:
        key = (case.institution_id, case.case_id)
        with self._lock:
            if key in self._cases:
                raise ConflictError(
                    "case_already_exists",
                    "A case with this identifier already exists in the institution.",
                    {"case_id": case.case_id},
                )
            self._cases[key] = case

    def get_case(self, case_id: str, institution_id: str) -> CaseRecord:
        with self._lock:
            try:
                return self._cases[(institution_id, case_id)]
            except KeyError as exc:
                raise NotFoundError(
                    "case_not_found",
                    "The case was not found inside the authorized institution scope.",
                    {"case_id": case_id},
                ) from exc

    def save_case(self, case: CaseRecord, *, expected_version: int) -> CaseRecord:
        key = (case.institution_id, case.case_id)
        with self._lock:
            current = self.get_case(case.case_id, case.institution_id)
            if current.version != expected_version:
                raise ConflictError(
                    "case_version_conflict",
                    "The case changed after it was read; reload before applying the update.",
                    {
                        "case_id": case.case_id,
                        "expected_version": expected_version,
                        "current_version": current.version,
                    },
                )
            saved = replace(case, version=expected_version + 1)
            self._cases[key] = saved
            return saved

    def append_safety_event(self, event: SafetyEvent) -> None:
        with self._lock:
            if event.safety_event_id in self._safety_events:
                raise ConflictError(
                    "safety_event_exists",
                    "The safety event identifier has already been used.",
                    {"safety_event_id": event.safety_event_id},
                )
            self._safety_events[event.safety_event_id] = event

    def append_team_review(self, review: TeamReviewVersion) -> None:
        key = (review.institution_id, review.case_id, review.review_group_id)
        with self._lock:
            if review.team_review_id in self._reviews:
                raise ConflictError(
                    "team_review_exists",
                    "The team review identifier has already been used.",
                    {"team_review_id": review.team_review_id},
                )
            self._reviews[review.team_review_id] = review
            self._review_groups[key].append(review.team_review_id)

    def get_team_review(self, review_id: str, institution_id: str, case_id: str) -> TeamReviewVersion:
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None or review.institution_id != institution_id or review.case_id != case_id:
                raise NotFoundError(
                    "team_review_not_found",
                    "The team review was not found inside the authorized case scope.",
                    {"team_review_id": review_id},
                )
            return review

    def get_latest_team_review(
        self, review_group_id: str, institution_id: str, case_id: str
    ) -> TeamReviewVersion | None:
        key = (institution_id, case_id, review_group_id)
        with self._lock:
            identifiers = self._review_groups.get(key, [])
            if not identifiers:
                return None
            return max((self._reviews[item] for item in identifiers), key=lambda review: review.version)

    def append_report(self, report: ReportVersion) -> None:
        key = (report.institution_id, report.case_id, report.report_id)
        with self._lock:
            if report.report_version_id in self._reports:
                raise ConflictError(
                    "report_version_exists",
                    "The report-version identifier has already been used.",
                    {"report_version_id": report.report_version_id},
                )
            self._reports[report.report_version_id] = report
            self._report_groups[key].append(report.report_version_id)

    def get_report_version(
        self, report_version_id: str, institution_id: str, case_id: str
    ) -> ReportVersion:
        with self._lock:
            report = self._reports.get(report_version_id)
            if report is None or report.institution_id != institution_id or report.case_id != case_id:
                raise NotFoundError(
                    "report_not_found",
                    "The report was not found inside the authorized case scope.",
                    {"report_version_id": report_version_id},
                )
            return report

    def get_latest_report(
        self, report_id: str, institution_id: str, case_id: str
    ) -> ReportVersion | None:
        key = (institution_id, case_id, report_id)
        with self._lock:
            identifiers = self._report_groups.get(key, [])
            if not identifiers:
                return None
            return max((self._reports[item] for item in identifiers), key=lambda report: report.version)

    def append_audit_event(self, event: AuditEvent) -> None:
        with self._lock:
            expected_previous = self._last_audit_hash.get(event.institution_id)
            if event.previous_event_hash != expected_previous:
                raise ConflictError(
                    "audit_chain_conflict",
                    "The audit chain changed before the event was appended.",
                    {"institution_id": event.institution_id},
                )
            if event.event_hash in self._last_audit_hash.values():
                raise ConflictError(
                    "audit_hash_reused",
                    "The audit-event hash has already been used.",
                    {"institution_id": event.institution_id},
                )
            self._audit_events.append(event)
            self._last_audit_hash[event.institution_id] = event.event_hash

    def last_audit_hash(self, institution_id: str) -> str | None:
        with self._lock:
            return self._last_audit_hash.get(institution_id)

    def audit_events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._audit_events)
