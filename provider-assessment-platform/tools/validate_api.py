#!/usr/bin/env python3
"""Validate the active OpenAPI contract with fail-closed governance rules.

The validator uses only the Python standard library. It checks internal
references and platform-specific safety invariants; it is not a replacement for
an OpenAPI parser, security review, or implementation conformance tests.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SPEC = ROOT / "api" / "openapi.v0.2.0.json"


class ApiValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ApiValidationFailure(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiValidationFailure(f"Invalid JSON in {path}: {exc}") from exc
    require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def operations(spec: Mapping[str, Any]) -> Iterable[tuple[str, str, Mapping[str, Any]]]:
    for path, path_item in spec.get("paths", {}).items():
        require(isinstance(path_item, Mapping), f"Path item {path} must be an object")
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if operation is not None:
                require(isinstance(operation, Mapping), f"{method.upper()} {path} must be an object")
                yield path, method, operation


def parameter_names(operation: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for parameter in operation.get("parameters", []):
        if not isinstance(parameter, Mapping):
            continue
        reference = parameter.get("$ref")
        if isinstance(reference, str):
            names.add(reference.rsplit("/", 1)[-1])
        elif isinstance(parameter.get("name"), str):
            names.add(parameter["name"])
    return names


def resolve_pointer(document: Any, reference: str) -> Any:
    require(reference.startswith("#/"), f"Only internal references are allowed: {reference}")
    current = document
    for raw_part in reference[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        require(isinstance(current, Mapping) and part in current, f"Unresolved reference: {reference}")
        current = current[part]
    return current


def walk(value: Any) -> Iterable[Any]:
    yield value
    if isinstance(value, Mapping):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def validate_references(spec: Mapping[str, Any]) -> None:
    for value in walk(spec):
        if isinstance(value, Mapping) and isinstance(value.get("$ref"), str):
            resolve_pointer(spec, value["$ref"])


def validate_urls(spec: Mapping[str, Any]) -> None:
    urls: list[str] = []
    for server in spec.get("servers", []):
        if isinstance(server, Mapping) and isinstance(server.get("url"), str):
            urls.append(server["url"])

    schemes = spec.get("components", {}).get("securitySchemes", {})
    for scheme in schemes.values():
        flows = scheme.get("flows", {}) if isinstance(scheme, Mapping) else {}
        for flow in flows.values():
            if not isinstance(flow, Mapping):
                continue
            for key in ("authorizationUrl", "tokenUrl", "refreshUrl"):
                if isinstance(flow.get(key), str):
                    urls.append(flow[key])

    require(urls, "The draft contract must declare non-routable placeholder URLs")
    for url in urls:
        parsed = urlparse(url)
        require(parsed.scheme == "https", f"API URLs must use HTTPS: {url}")
        require(parsed.hostname is not None and parsed.hostname.endswith(".invalid"), f"Draft API URL must use .invalid: {url}")


def validate_operations(spec: Mapping[str, Any]) -> None:
    seen_operation_ids: set[str] = set()
    prohibited_path_terms = re.compile(r"(?:diagnos|eligibility|auto[-_]?score|norm[-_]?table|test[-_]?item)", re.IGNORECASE)
    pure_check_paths = {"/cases/{case_id}/assessment-access-checks"}

    for path, method, operation in operations(spec):
        require(not prohibited_path_terms.search(path), f"Prohibited high-risk endpoint name: {path}")
        operation_id = operation.get("operationId")
        require(isinstance(operation_id, str) and operation_id, f"{method.upper()} {path} lacks operationId")
        require(operation_id not in seen_operation_ids, f"Duplicate operationId: {operation_id}")
        seen_operation_ids.add(operation_id)
        require(not prohibited_path_terms.search(operation_id), f"Prohibited high-risk operationId: {operation_id}")

        security = operation.get("security")
        require(isinstance(security, list) and security, f"{method.upper()} {path} must declare operation security")
        scopes = {
            scope
            for item in security
            if isinstance(item, Mapping)
            for listed in item.values()
            if isinstance(listed, list)
            for scope in listed
            if isinstance(scope, str)
        }
        require(scopes, f"{method.upper()} {path} must require at least one OAuth scope")

        names = parameter_names(operation)
        require("CorrelationId" in names or "X-Correlation-Id" in names, f"{method.upper()} {path} lacks correlation id")

        if method in {"post", "put", "delete"} and path not in pure_check_paths:
            require("IdempotencyKey" in names or "Idempotency-Key" in names, f"{method.upper()} {path} lacks idempotency key")
        if method == "patch":
            require("IfMatch" in names or "If-Match" in names, f"PATCH {path} lacks optimistic concurrency control")

        path_variables = set(re.findall(r"\{([^}]+)\}", path))
        declared_path_names: set[str] = set()
        for parameter in operation.get("parameters", []):
            if not isinstance(parameter, Mapping):
                continue
            if "$ref" in parameter:
                resolved = resolve_pointer(spec, parameter["$ref"])
                if isinstance(resolved, Mapping) and resolved.get("in") == "path":
                    declared_path_names.add(str(resolved.get("name")))
                    require(resolved.get("required") is True, f"Path parameter in {method.upper()} {path} must be required")
            elif parameter.get("in") == "path":
                declared_path_names.add(str(parameter.get("name")))
                require(parameter.get("required") is True, f"Path parameter in {method.upper()} {path} must be required")
        require(path_variables == declared_path_names, f"{method.upper()} {path} path parameters mismatch: expected {path_variables}, found {declared_path_names}")

        responses = operation.get("responses")
        require(isinstance(responses, Mapping) and responses, f"{method.upper()} {path} lacks responses")
        require("401" in responses and "403" in responses, f"{method.upper()} {path} must specify 401 and 403 responses")


def validate_sensitive_schemas(spec: Mapping[str, Any]) -> None:
    schemas = spec.get("components", {}).get("schemas", {})
    require(isinstance(schemas, Mapping), "components.schemas is required")

    forbidden_property_names = {
        "diagnosis",
        "diagnostic_conclusion",
        "automatic_diagnosis",
        "eligibility_decision",
        "test_item",
        "test_items",
        "prompt",
        "prompts",
        "answer_key",
        "norm_table",
        "norm_tables",
        "publisher_item_content",
    }

    for schema_name, schema in schemas.items():
        if not isinstance(schema, Mapping):
            continue
        for value in walk(schema):
            if not isinstance(value, Mapping):
                continue
            properties = value.get("properties")
            if isinstance(properties, Mapping):
                prohibited = forbidden_property_names.intersection(properties)
                require(not prohibited, f"Schema {schema_name} exposes prohibited fields: {sorted(prohibited)}")

    decision = schemas.get("PathwayDecision")
    require(isinstance(decision, Mapping), "PathwayDecision schema is required")
    decision_properties = decision.get("properties", {})
    truth = decision_properties.get("truth", {})
    require(truth.get("enum") == ["true", "false", "unknown"], "PathwayDecision must preserve true/false/unknown")
    decision_required = set(decision.get("required", []))
    require(
        {"requires_human_confirmation", "human_confirmation_received", "automation_blocked", "missing_fields"}.issubset(decision_required),
        "PathwayDecision must expose human gating, automation blocking, and missing fields",
    )

    draft = schemas.get("ReportDraft")
    require(isinstance(draft, Mapping) and "allOf" not in draft, "ReportDraft must be a direct, non-conflicting schema")
    require(draft.get("properties", {}).get("status", {}).get("const") == "draft", "ReportDraft status must be draft")
    require(draft.get("properties", {}).get("human_review_required", {}).get("const") is True, "ReportDraft must require human review")

    signed = schemas.get("SignedReport")
    require(isinstance(signed, Mapping) and "allOf" not in signed, "SignedReport must be a direct, non-conflicting schema")
    require(signed.get("properties", {}).get("status", {}).get("const") == "signed", "SignedReport status must be signed")
    require("professional_license_reference" in set(signed.get("required", [])), "SignedReport must record the professional license reference")
    require("content_hash" in set(signed.get("required", [])), "SignedReport must record the signed content hash")


def validate_report_signing(spec: Mapping[str, Any]) -> None:
    sign = spec.get("paths", {}).get("/cases/{case_id}/reports/{report_id}/sign", {}).get("post")
    require(isinstance(sign, Mapping), "Dedicated report-signing endpoint is required")
    security = sign.get("security", [])
    scopes = {
        scope
        for item in security
        if isinstance(item, Mapping)
        for listed in item.values()
        if isinstance(listed, list)
        for scope in listed
    }
    require("report:sign" in scopes, "Report signing must require report:sign")
    request_schema = (
        sign.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    require(request_schema.get("$ref") == "#/components/schemas/ReportSignRequest", "Report signing must use ReportSignRequest")


def main() -> int:
    try:
        require(ACTIVE_SPEC.is_file(), f"Active API contract is missing: {ACTIVE_SPEC}")
        spec = load_json(ACTIVE_SPEC)
        require(spec.get("openapi") == "3.1.0", "Active API must use OpenAPI 3.1.0")
        require(spec.get("info", {}).get("version") == "0.2.0", "Active API version must be 0.2.0")
        require(spec.get("security"), "A global security requirement is required")
        validate_references(spec)
        validate_urls(spec)
        validate_operations(spec)
        validate_sensitive_schemas(spec)
        validate_report_signing(spec)
    except ApiValidationFailure as exc:
        print(f"API VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    operation_count = sum(1 for _ in operations(spec))
    print(f"Validated active OpenAPI contract with {operation_count} secured operation(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
