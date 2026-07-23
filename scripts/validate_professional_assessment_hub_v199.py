from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

VERSION = 199
ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "professional-assessment-hub"
REQUIRED_FILES = ("index.html", "styles.css", "app.js", "catalog.json", "README.md")
ALLOWED_LICENSES = {
    "requires_publisher_license",
    "permission_required_before_embedding",
    "classification_public_reference_only",
    "internal_template",
    "requires_professional_service",
    "manual_rights_review",
}
FORBIDDEN_PATIENT_FIELDS = {
    "patientName",
    "nationalId",
    "medicalRecordNumber",
    "dateOfBirth",
    "phoneNumber",
    "emailAddress",
    "address",
}
REQUIRED_RULE_FRAGMENTS = (
    "لا تشخيص من مقياس واحد",
    "لا تُرقمن أداة",
    "أي خطر عاجل يوقف المسار",
    "الذكاء الاصطناعي لا يغيّر الدرجات",
)
REQUIRED_CONDITIONS = {
    "autism",
    "intellectual-disability",
    "adhd",
    "global-developmental-delay",
    "developmental-language-disorder",
    "specific-learning-disorder",
    "cerebral-palsy",
    "hearing-loss",
    "visual-impairment",
    "developmental-coordination-disorder",
    "behavior-challenging",
    "multiple-disabilities",
    "transition-adulthood",
}
APPROVED_SOURCE_HOSTS = {
    "www.who.int",
    "www.nice.org.uk",
    "publications.aap.org",
    "www.aaidd.org",
    "www.asha.org",
    "www.fda.gov",
    "www.w3.org",
    "www.testingstandards.net",
}


def load_catalog(hub: Path = HUB) -> dict:
    path = hub / "catalog.json"
    return json.loads(path.read_text(encoding="utf-8"))


def validate_files(hub: Path = HUB) -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_FILES:
        path = hub / name
        if not path.is_file():
            errors.append(f"missing file: {name}")
        elif path.stat().st_size == 0:
            errors.append(f"empty file: {name}")
    return errors


def validate_html(hub: Path = HUB) -> list[str]:
    errors: list[str] = []
    html = (hub / "index.html").read_text(encoding="utf-8")
    required = (
        '<html lang="ar" dir="rtl">',
        'name="robots" content="noindex,nofollow,noarchive"',
        "<h1>",
        'id="governanceRules"',
        'id="conditionList"',
        'id="instrumentList"',
        'id="simulationForm"',
        'id="courseList"',
        'id="qualityGates"',
        'src="app.js"',
        'href="styles.css"',
    )
    for marker in required:
        if marker not in html:
            errors.append(f"HTML missing marker: {marker}")
    if html.count("<h1>") != 1:
        errors.append("HTML must contain exactly one H1")
    for field in FORBIDDEN_PATIENT_FIELDS:
        if field in html:
            errors.append(f"forbidden patient field: {field}")
    if re.search(r'href=["\'](?:/pterminology-site/)?(?:index|encyclopedia|assessment-lab)', html):
        errors.append("hub must not link to public site before integration")
    return errors


def validate_catalog(catalog: dict) -> list[str]:
    errors: list[str] = []
    release = catalog.get("release", {})
    if release.get("version") != VERSION:
        errors.append("wrong release version")
    if release.get("public_navigation") is not False:
        errors.append("public_navigation must be false")
    if release.get("sitemap_registration") is not False:
        errors.append("sitemap_registration must be false")

    rules = catalog.get("governance", {}).get("non_negotiable_rules", [])
    rule_text = "\n".join(rules)
    for fragment in REQUIRED_RULE_FRAGMENTS:
        if fragment not in rule_text:
            errors.append(f"missing governance rule fragment: {fragment}")

    conditions = catalog.get("conditions", [])
    condition_ids = {item.get("id") for item in conditions}
    missing_conditions = sorted(REQUIRED_CONDITIONS - condition_ids)
    if missing_conditions:
        errors.append(f"missing conditions: {missing_conditions}")
    if len(condition_ids) != len(conditions):
        errors.append("duplicate condition ids")

    instrument_ids: set[str] = set()
    for instrument in catalog.get("instruments", []):
        instrument_id = instrument.get("id")
        if not instrument_id:
            errors.append("instrument without id")
            continue
        if instrument_id in instrument_ids:
            errors.append(f"duplicate instrument id: {instrument_id}")
        instrument_ids.add(instrument_id)
        if instrument.get("license_status") not in ALLOWED_LICENSES:
            errors.append(f"invalid license status: {instrument_id}")
        if instrument.get("license_status") != "internal_template":
            if instrument.get("digital_status") != "blocked_until_rights_and_local_validation":
                errors.append(f"unlicensed digital status not blocked: {instrument_id}")
        if not instrument.get("cautions"):
            errors.append(f"instrument lacks cautions: {instrument_id}")
        if not instrument.get("required_companions"):
            errors.append(f"instrument lacks companion assessments: {instrument_id}")

    for condition in conditions:
        steps = condition.get("steps", [])
        if len(steps) < 2:
            errors.append(f"condition requires at least two stages: {condition.get('id')}")
        if not condition.get("red_flags"):
            errors.append(f"condition lacks red flags: {condition.get('id')}")
        seen_steps: set[str] = set()
        for step in steps:
            step_id = step.get("id")
            if not step_id:
                errors.append(f"step without id in {condition.get('id')}")
            elif step_id in seen_steps:
                errors.append(f"duplicate step id {step_id} in {condition.get('id')}")
            seen_steps.add(step_id)
            if not step.get("completion"):
                errors.append(f"step lacks completion rule: {step_id}")
            if not step.get("next"):
                errors.append(f"step lacks next rule: {step_id}")
            for tool in step.get("candidate_tools", []):
                if tool not in instrument_ids:
                    errors.append(f"unknown tool {tool} referenced by {condition.get('id')}:{step_id}")

    course = catalog.get("course", [])
    if len(course) < 6:
        errors.append("course must contain at least six lessons")
    for lesson in course:
        if not lesson.get("knowledge_check"):
            errors.append(f"lesson lacks knowledge check: {lesson.get('id')}")

    gates = catalog.get("quality_gates", [])
    if len(gates) < 7:
        errors.append("at least seven quality gates required")

    source_hosts = {
        urlparse(item.get("url", "")).netloc
        for item in catalog.get("authoritative_sources", [])
        if item.get("url")
    }
    missing_hosts = sorted(APPROVED_SOURCE_HOSTS - source_hosts)
    if missing_hosts:
        errors.append(f"missing authoritative source hosts: {missing_hosts}")
    return errors


def validate_js(hub: Path = HUB) -> list[str]:
    errors: list[str] = []
    text = (hub / "app.js").read_text(encoding="utf-8")
    required = (
        'fetch("catalog.json"',
        "urgentRisk",
        "fictionalConsent",
        "لا تختار نسخة اختبار",
        "textContent",
    )
    for marker in required:
        if marker not in text:
            errors.append(f"JS missing safety marker: {marker}")
    forbidden = (
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "indexedDB",
        "document.cookie",
        'fetch("http:',
    )
    for marker in forbidden:
        if marker in text:
            errors.append(f"JS forbidden storage or unsafe rendering marker: {marker}")
    return errors


def run_validation(root: Path = ROOT) -> dict:
    hub = root / "professional-assessment-hub"
    errors = []
    errors.extend(validate_files(hub))
    if not errors:
        catalog = load_catalog(hub)
        errors.extend(validate_html(hub))
        errors.extend(validate_catalog(catalog))
        errors.extend(validate_js(hub))
    return {
        "version": VERSION,
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "hub": str(hub),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_validation(args.root.resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"professional assessment hub v{VERSION}: {report['status']}")
        for error in report["errors"]:
            print(f"- {error}")
    raise SystemExit(0 if report["status"] == "passed" else 1)


if __name__ == "__main__":
    main()
