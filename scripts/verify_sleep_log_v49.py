from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(text: str, pattern: str, message: str) -> None:
    if not re.search(pattern, text, re.I | re.S):
        raise AssertionError(message)


def write_minimal_sitemap(site: Path) -> None:
    site.mkdir(parents=True, exist_ok=True)
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
        encoding="utf-8",
    )


def main() -> None:
    # Build the tool into an isolated artifact. A clean GitHub Actions checkout
    # does not contain _site, so verification must create its own deterministic
    # baseline instead of depending on a prior production-build side effect.
    with tempfile.TemporaryDirectory(prefix="sleep-log-v49-") as tmp:
        site = Path(tmp) / "_site"
        write_minimal_sitemap(site)

        subprocess.run(
            [sys.executable, str(ROOT / "scripts/publish_daily_tools_v24.py"), str(site)],
            check=True,
        )
        subprocess.run(
            [sys.executable, str(ROOT / "scripts/publish_sleep_log_v49.py"), str(site)],
            check=True,
        )

        page = site / "daily-tools/sleep-wind-down-plan/index.html"
        if not page.is_file():
            raise AssertionError("sleep log page was not generated")

        text = page.read_text(encoding="utf-8")
        js = (ROOT / "assets/sleep-log-v49.js").read_text(encoding="utf-8")
        require(text, r'<html[^>]+lang="ar"[^>]+dir="rtl"', "Arabic RTL root missing")
        require(text, r"data-sleep-log", "interactive form missing")
        require(text, r'role="status"[^>]+aria-live="polite"', "live status missing")
        require(text, r"غير تشخيص", "non-diagnostic boundary missing")
        require(text, r"لا تُرسل البيانات إلى خادم", "local privacy statement missing")
        require(text, r"data-delete-sleep", "delete-all control missing")
        require(text, r"data-export-json", "JSON export missing")
        require(text, r"data-export-csv", "CSV export missing")
        require(text, r"data-print-sleep", "print control missing")
        require(text, r"prefers-reduced-motion", "reduced motion support missing")
        require(text, r"@media print", "print stylesheet missing")
        require(text, r"min-height:44px", "touch target baseline missing")
        require(text, r"خدمات الطوارئ المحلية", "urgent-help route missing")
        for field in ("date", "bedtime", "wakeTime", "quality", "energy", "note"):
            require(
                text,
                rf'name="{field}"[^>]+aria-describedby="[^"]+"',
                f"{field} must reference its error message",
            )
            require(text, rf'data-field-error="{field}"', f"{field} error container missing")
        require(js, r"setAttribute\('aria-invalid',\s*'true'\)", "invalid fields must expose aria-invalid")
        require(js, r"firstInvalid\.focus\(\)", "focus must move to the first invalid field")
        require(js, r"data-field-error", "field error rendering missing")
        if "fetch(" in js:
            raise AssertionError("network transmission is not allowed")

    subprocess.run(["node", str(ROOT / "tests/test_sleep_log_v49.mjs")], check=True)
    print("sleep-log-v49 verification passed")


if __name__ == "__main__":
    main()
