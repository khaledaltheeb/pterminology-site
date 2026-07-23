"""Application-service layer for the isolated provider assessment platform.

This package contains deterministic workflow rules only. It does not expose a
network service, perform diagnosis, calculate proprietary assessment scores, or
connect to production storage.
"""

from .domain import (
    ActorContext,
    CaseRecord,
    CaseStatus,
    ConsentSnapshot,
    ReportDraftInput,
    ReportStatus,
    ReviewInput,
    ReviewStatus,
    SafetyLevel,
)
from .errors import ConflictError, NotFoundError, PermissionDenied, ValidationError
from .transactional import ProviderAssessmentService
from .transactional_repository import AtomicInMemoryRepository

# Compatibility name for synthetic tests. The exported repository is atomic;
# the non-atomic base implementation remains internal and must not be used by
# package consumers.
InMemoryRepository = AtomicInMemoryRepository

__all__ = [
    "ActorContext",
    "AtomicInMemoryRepository",
    "CaseRecord",
    "CaseStatus",
    "ConflictError",
    "ConsentSnapshot",
    "InMemoryRepository",
    "NotFoundError",
    "PermissionDenied",
    "ProviderAssessmentService",
    "ReportDraftInput",
    "ReportStatus",
    "ReviewInput",
    "ReviewStatus",
    "SafetyLevel",
    "ValidationError",
]
