from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "provider-assessment-demo" / "professional-master-registry.js"


def main() -> None:
    text = REGISTRY.read_text(encoding="utf-8")

    forbidden = [
        "workflow_available_rights_required",
        'item.status=item.status==="external"?"external":"guide"',
        'item.activationStatus=item.status==="external"?"external_result_workflow":"workflow_available_review_required"',
    ]
    present = [token for token in forbidden if token in text]
    if present:
        raise SystemExit(f"Professional rights-lock regression detected: {present}")

    required = [
        '"activationStatus":"locked_pending_rights"',
        '"activationStatus":"locked_or_link_only"',
        'statusOf=s=>s==="external_result_import"',
        '"يتطلب تحققًا رسميًا من الترخيص والمؤهل وحق الرقمنة"',
        '"غير مفعّل كبنود اختبار داخل المنصة.',
    ]
    missing = [token for token in required if token not in text]
    if missing:
        raise SystemExit(f"Professional rights-lock contract missing: {missing}")

    licensed_inputs = re.findall(r'"inputMode":"([^"]*licensed[^"]*)"[^}]*?"activationStatus":"([^"]+)"', text)
    if not licensed_inputs:
        raise SystemExit("No licensed professional groups found")

    unsafe = [
        {"inputMode": input_mode, "activationStatus": status}
        for input_mode, status in licensed_inputs
        if status.startswith("workflow_available")
    ]
    if unsafe:
        raise SystemExit(f"Licensed groups exposed as available workflows: {unsafe}")

    print(
        {
            "version": 200,
            "licensed_groups_checked": len(licensed_inputs),
            "default_rights_lock": True,
            "runtime_override_blocked": True,
        }
    )


if __name__ == "__main__":
    main()
