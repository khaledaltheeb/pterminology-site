"""Deterministic audit-event hashing for the application service."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Mapping

from .domain import AuditEvent, ActorContext, immutable_mapping, utc_now


def _canonical_payload(
    *,
    audit_event_id: str,
    actor: ActorContext,
    action: str,
    object_type: str,
    object_id: str,
    reason: str,
    correlation_id: str,
    case_id: str | None,
    previous_event_hash: str | None,
    metadata: Mapping[str, str],
    occurred_at: datetime,
) -> bytes:
    value = {
        "action": action,
        "actor_provider_id": actor.provider_id,
        "audit_event_id": audit_event_id,
        "case_id": case_id,
        "correlation_id": correlation_id,
        "institution_id": actor.institution_id,
        "metadata": dict(sorted(metadata.items())),
        "object_id": object_id,
        "object_type": object_type,
        "occurred_at": occurred_at.isoformat(),
        "previous_event_hash": previous_event_hash,
        "reason": reason,
    }
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_audit_event(
    *,
    audit_event_id: str,
    actor: ActorContext,
    action: str,
    object_type: str,
    object_id: str,
    reason: str,
    correlation_id: str,
    case_id: str | None,
    previous_event_hash: str | None,
    metadata: Mapping[str, str] | None = None,
    occurred_at: datetime | None = None,
) -> AuditEvent:
    """Build a hash-linked event without including sensitive payload content."""

    at = occurred_at or utc_now()
    safe_metadata = immutable_mapping(metadata)
    payload = _canonical_payload(
        audit_event_id=audit_event_id,
        actor=actor,
        action=action,
        object_type=object_type,
        object_id=object_id,
        reason=reason,
        correlation_id=correlation_id,
        case_id=case_id,
        previous_event_hash=previous_event_hash,
        metadata=safe_metadata,
        occurred_at=at,
    )
    digest = hashlib.sha256(payload).hexdigest()
    return AuditEvent(
        audit_event_id=audit_event_id,
        institution_id=actor.institution_id,
        actor_provider_id=actor.provider_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        reason=reason,
        correlation_id=correlation_id,
        case_id=case_id,
        previous_event_hash=previous_event_hash,
        event_hash=digest,
        metadata=safe_metadata,
        occurred_at=at,
    )
