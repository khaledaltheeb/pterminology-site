"""Typed application errors with stable machine-readable codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class ServiceError(Exception):
    """Base error returned by the application layer.

    Error details must never contain protected test content, credentials, or
    direct identity data.
    """

    code: str
    message: str
    details: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class ValidationError(ServiceError):
    """Input or invariant validation failed."""


class PermissionDenied(ServiceError):
    """The actor is not permitted to perform the requested operation."""


class NotFoundError(ServiceError):
    """A resource was not found inside the actor's authorized scope."""


class ConflictError(ServiceError):
    """The requested operation conflicts with the current immutable state."""
