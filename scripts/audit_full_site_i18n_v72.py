#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "audit_full_site_v16.py"
LOCALE_CONTRACTS = {
    "en": ("en", "ltr"),
    "es": ("es", "ltr"),
}


def expected_language_direction(relative_path: str) -> tuple[str, str]:
    parts = Path(relative_path).parts
    if parts and parts[0] in LOCALE_CONTRACTS:
        return LOCALE_CONTRACTS[parts[0]]
    return "ar", "rtl"


def main() -> int:
    spec = importlib.util.spec_from_file_location("audit_full_site_v16_legacy", LEGACY)
    if spec is None or spec.loader is None:
        raise SystemExit("Could not load legacy full-site auditor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    original_parse_page = module.parse_page
    locale_page_counts: Counter[str] = Counter()
    contract_errors: list[str] = []

    def locale_aware_parse_page(path: Path):
        parser = original_parse_page(path)
        rel = path.relative_to(module.SITE).as_posix()
        expected_lang, expected_dir = expected_language_direction(rel)
        locale_page_counts[expected_lang] += 1
        actual_lang = parser.html_attrs.get("lang")
        actual_dir = parser.html_attrs.get("dir")
        if actual_lang != expected_lang or actual_dir != expected_dir:
            contract_errors.append(
                f"Locale contract mismatch in {rel}: expected {expected_lang}/{expected_dir}, "
                f"found {actual_lang}/{actual_dir}"
            )
        # The v16 auditor predates multilingual output and checks only ar/rtl.
        # Normalize only the parser view after validating the real document above;
        # every other metadata, link, content and accessibility check remains unchanged.
        parser.html_attrs = dict(parser.html_attrs)
        parser.html_attrs["lang"] = "ar"
        parser.html_attrs["dir"] = "rtl"
        return parser

    module.parse_page = locale_aware_parse_page
    result = module.main()

    if contract_errors:
        raise SystemExit("\n".join(contract_errors[:80]))

    report_path = module.SITE / "api" / "full-site-audit-v16.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["version"] = "16-i18n-v72"
    report["locale_contracts"] = {
        "ar": {"lang": "ar", "dir": "rtl"},
        **{
            locale: {"lang": contract[0], "dir": contract[1]}
            for locale, contract in LOCALE_CONTRACTS.items()
        },
    }
    report["locale_page_counts"] = dict(sorted(locale_page_counts.items()))
    report["locale_contract_error_count"] = 0
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "audit": "passed",
                "version": report["version"],
                "locale_page_counts": report["locale_page_counts"],
                "locale_contract_error_count": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return int(result or 0)


if __name__ == "__main__":
    raise SystemExit(main())
