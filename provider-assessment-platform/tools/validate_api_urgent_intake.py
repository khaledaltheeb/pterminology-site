#!/usr/bin/env python3
"""Validate conditional urgent and emergency intake handoff requirements."""

from __future__ import annotations

import sys
from typing import Mapping, Sequence

from validate_api import ApiValidationFailure, load_effective_contract, require


def main() -> int:
    try:
        manifest, spec = load_effective_contract()
        require(
            manifest.get("effective_version") == "0.2.4",
            "Urgent intake handoff must be active in API version 0.2.4",
        )
        gates = set(manifest.get("required_verification", []))
        require(
            {"urgent_intake_domains_observations_handoff", "atomic_case_and_urgent_safety_event"}.issubset(gates),
            "API manifest lacks urgent intake verification gates",
        )

        schema = (
            spec.get("components", {})
            .get("schemas", {})
            .get("SafetyIntakeRequest")
        )
        require(isinstance(schema, Mapping), "SafetyIntakeRequest schema is required")
        properties = schema.get("properties", {})
        require(isinstance(properties, Mapping), "SafetyIntakeRequest properties are required")
        for field in ("domains", "observations", "handoff_target"):
            require(field in properties, f"Urgent intake field is missing: {field}")
        require(
            properties.get("domains", {}).get("minItems") == 1,
            "Urgent intake domains must contain at least one value",
        )
        require(
            properties.get("observations", {}).get("minLength") == 10,
            "Urgent intake observations must be specific",
        )
        require(
            properties.get("handoff_target", {}).get("minLength") == 3,
            "Urgent intake handoff target must be meaningful",
        )

        conditions = schema.get("allOf")
        require(isinstance(conditions, Sequence) and len(conditions) == 1, "One urgent intake conditional rule is required")
        conditional = conditions[0]
        require(isinstance(conditional, Mapping), "Urgent intake conditional rule is invalid")
        urgent_levels = (
            conditional.get("if", {})
            .get("properties", {})
            .get("level", {})
            .get("enum")
        )
        require(
            set(urgent_levels or []) == {"urgent", "emergency"},
            "Conditional urgent intake levels are incomplete",
        )
        urgent_required = set(conditional.get("then", {}).get("required", []))
        require(
            urgent_required == {"domains", "observations", "handoff_target"},
            f"Urgent intake conditional requirements are invalid: {sorted(urgent_required)}",
        )
        description = str(schema.get("description", ""))
        require(
            "atomically" in description
            and "immutable safety event" in description,
            "Urgent intake contract must state atomic case and safety-event creation",
        )
    except ApiValidationFailure as exc:
        print(f"API URGENT INTAKE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated urgent and emergency intake domains, observations, handoff, and atomic event contract.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
