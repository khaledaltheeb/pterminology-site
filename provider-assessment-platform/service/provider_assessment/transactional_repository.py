"""Atomic test repository for compound provider-assessment workflows.

This repository remains strictly synthetic and in-memory. It exists to prove
transaction boundaries before a PostgreSQL adapter is allowed to implement the
same application-service port.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from typing import Iterator

from .domain import ActorContext
from .repository import InMemoryRepository


class AtomicInMemoryRepository(InMemoryRepository):
    """In-memory repository with rollback for one compound service operation.

    Domain records are immutable, so shallow copies of record dictionaries plus
    independent copies of index lists are sufficient for deterministic rollback.
    The inherited ``RLock`` makes nested repository calls safe inside the same
    transaction boundary. ``actor`` is accepted to match the production port;
    synthetic storage does not use it to authorize access.
    """

    @contextmanager
    def atomic(
        self,
        *,
        actor: ActorContext | None = None,
    ) -> Iterator[None]:
        del actor
        with self._lock:
            snapshot = {
                "cases": dict(self._cases),
                "safety_events": dict(self._safety_events),
                "reviews": dict(self._reviews),
                "review_groups": defaultdict(
                    list,
                    {key: list(value) for key, value in self._review_groups.items()},
                ),
                "reports": dict(self._reports),
                "report_groups": defaultdict(
                    list,
                    {key: list(value) for key, value in self._report_groups.items()},
                ),
                "audit_events": list(self._audit_events),
                "last_audit_hash": dict(self._last_audit_hash),
            }
            try:
                yield
            except BaseException:
                self._cases = snapshot["cases"]
                self._safety_events = snapshot["safety_events"]
                self._reviews = snapshot["reviews"]
                self._review_groups = snapshot["review_groups"]
                self._reports = snapshot["reports"]
                self._report_groups = snapshot["report_groups"]
                self._audit_events = snapshot["audit_events"]
                self._last_audit_hash = snapshot["last_audit_hash"]
                raise

    def safety_events(self) -> tuple[object, ...]:
        """Return immutable synthetic-test inspection data."""

        with self._lock:
            return tuple(self._safety_events.values())

    def team_reviews(self) -> tuple[object, ...]:
        """Return immutable synthetic-test inspection data."""

        with self._lock:
            return tuple(self._reviews.values())

    def reports(self) -> tuple[object, ...]:
        """Return immutable synthetic-test inspection data."""

        with self._lock:
            return tuple(self._reports.values())
