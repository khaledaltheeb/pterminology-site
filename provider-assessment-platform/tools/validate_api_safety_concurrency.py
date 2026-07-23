#!/usr/bin/env python3
"""Validate optimistic concurrency for safety-event writes."""

from __future__ import annotations

import sys
from typing import Mapping

from validate_api import ApiValidationFailure, load_effective_contract, require


def main() -> int:
    try:
        manifest, spec = load_effective_contract()
        require(
            manifest.get("effective_version") == "0.2.3",
            "Safety concurrency must be active in API version 0.2.3",
        )
        gates = set(manifest.get("required_verification", []))
        require(
            {"safety_optimistic_concurrency", "safety_response_version_and_etag"}.issubset(gates),
            "API manifest lacks safety concurrency verification gates",
        )

        schemas = spec.get("components", {}).get("schemas", {})
        request = schemas.get("SafetyEventRequest")
        response = schemas.get("SafetyEvent")
        require(isinstance(request, Mapping), "SafetyEventRequest schema is required")
        require(isinstance(response, Mapping), "SafetyEvent schema is required")

        request_required = set(request.get("required", []))
        response_required = set(response.get("required", []))
        require("case_version" in request_required, "SafetyEventRequest must require case_version")
        require("case_version" in response_required, "SafetyEvent must return case_version")
        for name, schema in (("request", request), ("response", response)):
            case_version = schema.get("properties", {}).get("case_version")
            require(isinstance(case_version, Mapping), f"Safety event {name} case_version is missing")
            require(case_version.get("type") == "integer", f"Safety event {name} case_version must be integer")
            require(case_version.get("minimum") == 1, f"Safety event {name} case_version minimum must be 1")

        create_response = (
            spec.get("paths", {})
            .get("/cases/{case_id}/safety-events", {})
            .get("post", {})
            .get("responses", {})
            .get("201", {})
        )
        require(isinstance(create_response, Mapping), "Safety-event 201 response is required")
        etag = create_response.get("headers", {}).get("ETag")
        require(
            isinstance(etag, Mapping)
            and etag.get("$ref") == "#/components/headers/ETag",
            "Safety-event creation must return the case ETag",
        )
    except ApiValidationFailure as exc:
        print(f"API SAFETY CONCURRENCY VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated safety-event case_version input, returned version, and ETag concurrency evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
