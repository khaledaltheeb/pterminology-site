#!/usr/bin/env python3
"""Validate the effective OpenAPI contract with fail-closed governance rules.

The active contract is a reviewed base specification plus ordered JSON Patch
operations declared in ``api/CONTRACT_MANIFEST.json``. The validator uses only
the Python standard library. It is not a replacement for an OpenAPI parser,
implementation conformance tests, or an independent security review.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, MutableSequence
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "api"
CONTRACT_MANIFEST = API_DIR / "CONTRACT_MANIFEST.json"


class ApiValidationFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ApiValidationFailure(message)


def load_json_value(path: Path) -> Any:
    require(path.is_file(), f"Missing JSON file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiValidationFailure(f"Invalid JSON in {path}: {exc}") from exc


def load_json_object(path: Path) -> dict[str, Any]:
    value = load_json_value(path)
    require(isinstance(value, dict), f"{path} must contain a JSON object")
    return value


def decode_pointer_part(raw: str) -> str:
    return raw.replace("~1", "/").replace("~0", "~")


def resolve_patch_parent(document: Any, path: str) -> tuple[Any, str]:
    require(path.startswith("/"), f"JSON Patch path must be absolute: {path}")
    parts = [decode_pointer_part(part) for part in path[1:].split("/")]
    require(bool(parts), "JSON Patch cannot replace the complete document")
    current = document
    for part in parts[:-1]:
        if isinstance(current, Mapping):
            require(part in current, f"JSON Patch parent does not exist: {path}")
            current = current[part]
        elif isinstance(current, list):
            require(part.isdigit(), f"JSON Patch list index is invalid: {path}")
            index = int(part)
            require(0 <= index < len(current), f"JSON Patch list index is out of range: {path}")
            current = current[index]
        else:
            raise ApiValidationFailure(f"JSON Patch traverses a scalar value: {path}")
    return current, parts[-1]


def apply_json_patch(document: Mapping[str, Any], patch: Any, *, source: Path) -> dict[str, Any]:
    require(isinstance(patch, list), f"{source} must contain a JSON Patch array")
    result: Any = copy.deepcopy(document)
    for index, operation in enumerate(patch):
        require(isinstance(operation, Mapping), f"{source} operation {index} must be an object")
        op = operation.get("op")
        path = operation.get("path")
        require(op in {"add", "replace", "remove"}, f"{source} operation {index} uses unsupported op: {op}")
        require(isinstance(path, str), f"{source} operation {index} lacks path")
        parent, key = resolve_patch_parent(result, path)

        if isinstance(parent, MutableSequence):
            if op == "add" and key == "-":
                parent.append(copy.deepcopy(operation.get("value")))
                continue
            require(key.isdigit(), f"{source} operation {index} has invalid list index")
            list_index = int(key)
            if op == "add":
                require(0 <= list_index <= len(parent), f"{source} add index is out of range")
                parent.insert(list_index, copy.deepcopy(operation.get("value")))
            elif op == "replace":
                require(0 <= list_index < len(parent), f"{source} replace index is out of range")
                require("value" in operation, f"{source} replace operation lacks value")
                parent[list_index] = copy.deepcopy(operation["value"])
            else:
                require(0 <= list_index < len(parent), f"{source} remove index is out of range")
                del parent[list_index]
            continue

        require(isinstance(parent, MutableMapping), f"{source} patch parent must be an object or array")
        if op == "add":
            require("value" in operation, f"{source} add operation lacks value")
            parent[key] = copy.deepcopy(operation["value"])
        elif op == "replace":
            require(key in parent, f"{source} replace target does not exist: {path}")
            require("value" in operation, f"{source} replace operation lacks value")
            parent[key] = copy.deepcopy(operation["value"])
        else:
            require(key in parent, f"{source} remove target does not exist: {path}")
            del parent[key]

    require(isinstance(result, dict), "Effective OpenAPI document must remain an object")
    return result


def load_effective_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = load_json_object(CONTRACT_MANIFEST)
    require(manifest.get("status") == "active-draft", "API contract must remain active-draft")
    require(manifest.get("approved_for_production") is False, "Draft API contract cannot be production-approved")
    base_name = manifest.get("base_spec")
    require(isinstance(base_name, str) and base_name, "Contract manifest must declare base_spec")
    base_path = API_DIR / base_name
    spec = load_json_object(base_path)

    patches = manifest.get("ordered_patches")
    require(isinstance(patches, list) and patches, "Contract manifest must declare ordered patches")
    require(len(patches) == len(set(patches)), "Contract patch list contains duplicates")
    for patch_name in patches:
        require(isinstance(patch_name, str) and patch_name, "Patch file name is invalid")
        patch_path = API_DIR / patch_name
        spec = apply_json_patch(spec, load_json_value(patch_path), source=patch_path)

    effective_version = manifest.get("effective_version")
    require(spec.get("info", {}).get("version") == effective_version, "Effective API version does not match manifest")
    return manifest, spec


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
        part = decode_pointer_part(raw_part)
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


def validate_unique_required(schema_name: str, schema: Mapping[str, Any]) -> set[str]:
    required = schema.get("required", [])
    require(isinstance(required, list), f"{schema_name}.required must be an array")
    require(len(required) == len(set(required)), f"{schema_name}.required contains duplicates")
    return set(required)


def validate_intake_contract(spec: Mapping[str, Any]) -> None:
    schemas = spec.get("components", {}).get("schemas", {})
    case_create = schemas.get("CaseCreateRequest")
    subject = schemas.get("Subject")
    consent = schemas.get("Consent")
    referral = schemas.get("Referral")
    safety = schemas.get("SafetySnapshot")
    for name, schema in (
        ("CaseCreateRequest", case_create),
        ("Subject", subject),
        ("Consent", consent),
        ("Referral", referral),
        ("SafetySnapshot", safety),
    ):
        require(isinstance(schema, Mapping), f"{name} schema is required")

    require(
        {"identity_vault_reference", "subject", "consent", "referral", "safety"}.issubset(
            validate_unique_required("CaseCreateRequest", case_create)
        ),
        "Case creation must require identity vault, subject, consent, referral, and safety blocks",
    )
    identity = case_create.get("properties", {}).get("identity_vault_reference", {})
    require(identity.get("type") == "string", "Identity vault reference must be a string")
    require(identity.get("pattern") == "^[A-Z][A-Z0-9:_./-]{5,249}$", "Identity vault reference must be an opaque constrained reference")

    require(
        {
            "date_of_birth",
            "age_months_at_intake",
            "preferred_language",
            "home_languages",
            "education_languages",
            "communication_modes",
            "country_of_service",
        }.issubset(validate_unique_required("Subject", subject)),
        "Subject must explicitly include age, languages, communication, and service country",
    )
    require(
        {"legal_basis", "obtained_at", "scope", "withdrawal_explained", "document_reference"}.issubset(
            validate_unique_required("Consent", consent)
        ),
        "Consent must require its evidence document reference",
    )
    require(
        {"reason", "questions", "referrer_role", "urgency"}.issubset(
            validate_unique_required("Referral", referral)
        ),
        "Referral must require an explicit urgency",
    )

    safety_required = validate_unique_required("SafetySnapshot", safety)
    require({"level", "screened_at", "screened_by", "actions"}.issubset(safety_required), "Safety snapshot is incomplete")
    safety_properties = safety.get("properties", {})
    require(safety_properties.get("screened_at", {}).get("readOnly") is True, "Safety screened_at must be server-attested read-only data")
    require(safety_properties.get("screened_by", {}).get("readOnly") is True, "Safety screened_by must be server-attested read-only data")
    require(safety_properties.get("actions", {}).get("minItems") == 1, "Safety actions or no-action decision must be non-empty")


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
        manifest, spec = load_effective_contract()
        require(spec.get("openapi") == "3.1.0", "Active API must use OpenAPI 3.1.0")
        require(spec.get("security"), "A global security requirement is required")
        required_verification = set(manifest.get("required_verification", []))
        for item in (
            "json_patch_application",
            "internal_reference_resolution",
            "secured_operation_validation",
            "intake_contract_alignment",
            "read_only_server_attestation_fields",
            "implementation_conformance_tests",
            "independent_api_security_review",
        ):
            require(item in required_verification, f"API manifest is missing verification gate: {item}")
        validate_references(spec)
        validate_urls(spec)
        validate_operations(spec)
        validate_intake_contract(spec)
        validate_sensitive_schemas(spec)
        validate_report_signing(spec)
    except ApiValidationFailure as exc:
        print(f"API VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    operation_count = sum(1 for _ in operations(spec))
    print(
        f"Validated effective OpenAPI {spec['info']['version']} contract with "
        f"{operation_count} secured operation(s) from governed base and patch files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
