#!/usr/bin/env python3
"""Fail-closed validation for provider-assessment governance documents."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GovernanceFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GovernanceFailure(message)


def read(relative: str) -> str:
    path = ROOT / relative
    require(path.is_file(), f"Missing governance file: {relative}")
    text = path.read_text(encoding="utf-8")
    require(text.strip(), f"Empty governance file: {relative}")
    return text


def require_sections(text: str, sections: tuple[str, ...], label: str) -> None:
    missing = [section for section in sections if section not in text]
    require(not missing, f"{label} is missing required sections or concepts: {missing}")


def main() -> int:
    try:
        threat = read("security/threat-model-ar.md")
        dpia = read("security/dpia-template-ar.md")
        incident = read("security/incident-response-ar.md")
        onboarding = read("governance/institution-onboarding-ar.md")
        activation = read("governance/assessment-activation-gate-ar.md")
        safety_case = read("governance/clinical-safety-case-ar.md")

        require_sections(
            threat,
            (
                "حدود الثقة",
                "أخطار السلامة السريرية",
                "ضوابط الذكاء الاصطناعي",
                "اختبارات الأمن الدنيا",
                "لا يسمح ببيانات حقيقية قبل",
            ),
            "Threat model",
        )
        for hazard_id in ("H-01", "H-02", "H-03", "H-04", "H-05", "H-06"):
            require(hazard_id in threat, f"Threat model is missing clinical hazard {hazard_id}")
        require("BYPASSRLS" in threat, "Threat model must prohibit privilege elevation around RLS")
        require("أداة منفردة" in threat, "Threat model must address single-tool conclusions")

        require_sections(
            dpia,
            (
                "وصف المعالجة",
                "فئات البيانات",
                "الضرورة والتناسب",
                "حقوق الأشخاص",
                "تقييم المخاطر",
                "حماية الأطفال",
                "الذكاء الاصطناعي",
                "القرار",
            ),
            "DPIA template",
        )
        require(dpia.count("PENDING") >= 20, "DPIA must remain an unapproved template with explicit pending fields")
        require("تدريب الذكاء الاصطناعي" in dpia and "ممنوع افتراضيًا" in dpia, "DPIA must default AI training to prohibited")
        require("لا تدمج الموافقة على الخدمة مع البحث" in dpia, "DPIA must separate service and research consent")

        require_sections(
            incident,
            (
                "مستويات الخطورة",
                "الاحتواء الفوري",
                "حفظ الأدلة",
                "مسار السلامة السريرية",
                "إخطار الخصوصية والقانون",
                "الاستئصال والاستعادة",
                "المراجعة بعد الحادث",
                "سيناريوهات التمرين",
            ),
            "Incident response plan",
        )
        require("لا تعتمد المنصة موعدًا قانونيًا عالميًا واحدًا" in incident, "Incident plan must not invent a universal legal deadline")
        require("لا يعدّل التقرير الموقع" in incident, "Incident plan must preserve signed-report history")

        require_sections(
            onboarding,
            (
                "حالات المؤسسة",
                "الحوكمة السريرية",
                "الخصوصية والقانون",
                "اختبار القبول المؤسسي",
                "بوابة التفعيل",
                "المراقبة المستمرة",
                "التعليق أو الإيقاف",
                "إنهاء العلاقة",
            ),
            "Institution onboarding",
        )
        require("لا يتيح توقيع عقد تجاري وحده" in onboarding, "Commercial contract must not automatically enable access")
        require("كل أداة لها تفويض مستقل" in onboarding, "Institution approval must not enable every assessment")

        require_sections(
            activation,
            (
                "الملكية والترخيص",
                "أمن الاختبار",
                "المؤهلات والتدريب",
                "السكان واللغة والمعايير",
                "الأدلة السيكومترية",
                "التصحيح والتحويل",
                "الربط بالمسار",
                "اختبارات الفشل",
                "قرار التفعيل",
                "التعليق والتقاعد",
            ),
            "Assessment activation gate",
        )
        require("عند غياب دليل واضح، تكون الأداة `disabled`" in activation, "Assessment activation must fail closed")
        require("يحظر: `نتيجة مرتفعة → تشخيص`" in activation, "Assessment gate must prohibit score-to-diagnosis shortcuts")
        require("الترجمة الفورية أو غير المقننة" in activation, "Assessment gate must address invalid translated norms")

        require_sections(
            safety_case,
            (
                "C0 — المنصة آمنة بما يكفي",
                "NOT_PROVEN",
                "C1 — التفويض المهني والمؤسسي",
                "C2 — صحة الحالة والهوية والموافقة",
                "C3 — السلامة العاجلة",
                "C4 — كفاية وصلاحية الأدلة",
                "C5 — صحة وقابلية تفسير قواعد الانتقال",
                "C6 — سلامة التقرير والتوقيع",
                "C7 — الأمن والخصوصية",
                "C8 — الإتاحة وصلاحية التكييف",
                "C9 — الأعطال والحوادث والتصحيح",
                "C10 — المراقبة والإنصاف بعد الإطلاق",
                "بوابة إطلاق السلامة",
            ),
            "Clinical safety case",
        )
        require("C0 السلامة الكلية" in safety_case, "Safety case must include an argument tree")
        require("غير مثبت" in safety_case, "Safety case must not imply approval")
        require("NOT SUPPORTED" in safety_case, "Unsupported claims must remain explicit")
        require("لا يسمح بالانتقال من بيانات صناعية" in safety_case, "Safety case must gate real-data pilots")

        all_text = "\n".join((threat, dpia, incident, onboarding, activation, safety_case))
        prohibited_claims = (
            "معتمد عالميًا",
            "معتمد سريريًا",
            "خالي من المخاطر",
            "يضمن عدم الخطأ",
            "تشخيص تلقائي آمن",
            "موافق عليه من وزارة الصحة",
        )
        for claim in prohibited_claims:
            require(claim not in all_text, f"Unsupported governance claim found: {claim}")

        hardcoded_legal_deadline = re.compile(
            r"(?:يجب|يلزم)\s+(?:الإبلاغ|الإخطار)\s+(?:خلال|في غضون)\s+\d+\s+(?:ساعة|ساعات|يوم|أيام)",
            flags=re.IGNORECASE,
        )
        require(not hardcoded_legal_deadline.search(all_text), "Governance documents must not invent a universal legal notification deadline")

        manifest_path = ROOT / "database" / "MIGRATION_MANIFEST.json"
        require(manifest_path.is_file(), "Database migration manifest is required by the safety case")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        require(manifest.get("active_baseline", {}).get("approved_for_production") is False, "Governance cannot coexist with a production-approved draft database")
    except (GovernanceFailure, json.JSONDecodeError) as exc:
        print(f"GOVERNANCE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated threat model, DPIA template, incident response, institutional gate, assessment gate, and clinical safety case.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
