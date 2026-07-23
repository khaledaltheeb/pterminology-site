"""Atomic facade for compound provider-assessment application workflows."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol

from .application import ProviderAssessmentService as BaseProviderAssessmentService


class AtomicRepository(Protocol):
    def atomic(self) -> AbstractContextManager[None]: ...


class ProviderAssessmentService(BaseProviderAssessmentService):
    """Fail-closed service whose public writes commit or roll back as one unit.

    The base service contains the workflow rules. This facade supplies the
    transaction boundary. Production adapters must implement ``atomic()`` with a
    real database transaction and must append the audit event in that same
    transaction.
    """

    def __init__(self, repository: AtomicRepository, **kwargs: Any) -> None:
        if not callable(getattr(repository, "atomic", None)):
            raise TypeError(
                "ProviderAssessmentService requires a repository with an atomic() transaction boundary"
            )
        super().__init__(repository, **kwargs)

    def create_case(self, **kwargs: Any):
        with self._repository.atomic():
            return super().create_case(**kwargs)

    def record_safety_event(self, **kwargs: Any):
        with self._repository.atomic():
            return super().record_safety_event(**kwargs)

    def create_team_review_version(self, **kwargs: Any):
        with self._repository.atomic():
            return super().create_team_review_version(**kwargs)

    def create_report_draft(self, **kwargs: Any):
        with self._repository.atomic():
            return super().create_report_draft(**kwargs)

    def sign_report(self, **kwargs: Any):
        with self._repository.atomic():
            return super().sign_report(**kwargs)
