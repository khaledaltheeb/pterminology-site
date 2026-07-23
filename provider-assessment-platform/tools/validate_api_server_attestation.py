#!/usr/bin/env python3
"""Validate separation of client safety input and server-attested output."""

from __future__ import annotations

import sys
from typing import Mapping

from validate_api import (
    ApiValidationFailure,
    load_effective_contract,
    require,
)


def main() -> int:
    try:
        manifest, spec = load_effective_contract()
        require(
            manifest.get("effective_version") == "0.2.2",
            "Server-attested safety must be active in API version 0.2.2",
        )
        require(
            "separate_safety_request_and_snapshot"
            in set(manifest.get("required_verification", [])),
            "API manifest lacks the safety request/snapshot separation gate",
        )

        schemas = spec.get("components", {}).get("schemas", {})
        require(isinstance(schemas, Mapping), "API schemas are required")
        case_create = schemas.get("CaseCreateRequest")
        safety_request = schemas.get("SafetyIntakeRequest")
        safety_snapshot = schemas.get("SafetySnapshot")
        for name, schema in (
            ("CaseCreateRequest", case_create),
            ("SafetyIntakeRequest", safety_request),
            ("SafetySnapshot", safety_snapshot),
        ):
            require(isinstance(schema, Mapping), f"{name} must be an object schema")

        safety_reference = (
            case_create.get("properties", {})
            .get("safety", {})
            .get("$ref")
        )
        require(
            safety_reference == "#/components/schemas/SafetyIntakeRequest",
            "Case creation must use the client-only safety request schema",
        )

        request_required = set(safety_request.get("required", []))
        request_properties = safety_request.get("properties", {})
        require(
            request_required == {"level", "actions"},
            f"SafetyIntakeRequest required fields are invalid: {sorted(request_required)}",
        )
        require(
            safety_request.get("additionalProperties") is False,
            "SafetyIntakeRequest must reject undeclared client fields",
        )
        require(
            "screened_at" not in request_properties
            and "screened_by" not in request_properties,
            "Client safety input must not accept server-attested fields",
        )
        require(
            request_properties.get("actions", {}).get("minItems") == 1,
            "Client safety input must document an action or explicit no-action decision",
        )

        snapshot_required = set(safety_snapshot.get("required", []))
        snapshot_properties = safety_snapshot.get("properties", {})
        require(
            {"level", "actions", "screened_at", "screened_by"}.issubset(
                snapshot_required
            ),
            "SafetySnapshot must contain the full attested result",
        )
        require(
            snapshot_properties.get("screened_at", {}).get("readOnly") is True,
            "SafetySnapshot.screened_at must remain read-only",
        )
        require(
            snapshot_properties.get("screened_by", {}).get("readOnly") is True,
            "SafetySnapshot.screened_by must remain read-only",
        )
    except ApiValidationFailure as exc:
        print(f"API SAFETY ATTESTATION VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated client-only safety intake and server-attested safety snapshot separation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
