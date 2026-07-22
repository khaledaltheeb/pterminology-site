from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(text: str, pattern: str, message: str) -> None:
    if not re.search(pattern, text, re.I | re.S):
        raise AssertionError(message)


def visible_word_count(text: str) -> int:
    cleaned = re.sub(r"<(script|style|svg)\b[^>]*>.*?</\1>", " ", text, flags=re.I | re.S)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = unescape(cleaned)
    return len(re.findall(r"[\w\u0600-\u06ff]+", cleaned, re.UNICODE))


def write_minimal_sitemap(site: Path) -> None:
    site.mkdir(parents=True, exist_ok=True)
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></sitemapindex>\n',
        encoding="utf-8",
    )


def patch_generated_page(site: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/patch_sleep_svg_export_v65.py"), str(site)],
        check=True,
    )


def verify_generated_page(site: Path) -> int:
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
    require(text, r"data-export-svg", "SVG export missing from generated production page")
    require(
        text,
        r'data-export-svg[^>]+aria-describedby="sleep-svg-export-privacy"',
        "SVG export must reference its privacy disclosure",
    )
    require(text, r'id="sleep-svg-export-privacy"', "SVG privacy disclosure missing")
    require(text, r"يتضمن تواريخ النوم ومدته ودرجات الجودة والطاقة", "SVG exported fields disclosure missing")
    require(text, r"لا يتضمن الملاحظات النصية", "SVG notes exclusion disclosure missing")
    require(text, r"راجع الملف قبل مشاركته", "SVG review-before-sharing guidance missing")
    require(text, r"المشاركة اختيارية", "optional sharing boundary missing")
    require(text, r"خارج التخزين المحلي", "external sharing boundary missing")
    require(text, r"data-print-sleep", "print control missing")
    require(text, r"prefers-reduced-motion", "reduced motion support missing")
    require(text, r"@media print", "print stylesheet missing")
    require(text, r"min-height:44px", "touch target baseline missing")
    require(text, r"خدمات الطوارئ المحلية", "urgent-help route missing")
    require(text, r"كيف تقرأ السجل دون مبالغة", "interpretation guidance missing")
    require(text, r"خطة استخدام لمدة أسبوعين", "two-week use plan missing")
    require(text, r"ما الذي يُفعل وما الذي يُتجنب", "do and avoid guidance missing")
    require(text, r"متى تحتاج إلى مساعدة مهنية", "professional-help section missing")
    require(text, r"أسئلة شائعة", "FAQ section missing")
    require(text, r"آخر مراجعة تحريرية:</strong>\s*22 يوليو 2026", "review date missing")
    for source in (
        "nhlbi.nih.gov/resources/sleep-diary",
        "nhlbi.nih.gov/health/insomnia/diagnosis",
        "aasm.org/clinical-resources/practice-standards/practice-guidelines",
        "cdc.gov/sleep/data-research/facts-stats/adults-sleep-facts-and-stats",
    ):
        require(text, re.escape(source), f"authoritative source missing: {source}")
    words = visible_word_count(text)
    if words < 800:
        raise AssertionError(f"sleep log explanatory content remains thin: {words} visible words")
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
    return words


def main() -> None:
    production_site = ROOT / "_site"
    production_page = production_site / "daily-tools/sleep-wind-down-plan/index.html"
    if production_page.is_file():
        patch_generated_page(production_site)
        verify_generated_page(production_site)

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
        patch_generated_page(site)
        words = verify_generated_page(site)

    subprocess.run(["node", str(ROOT / "tests/test_sleep_log_v49.mjs")], check=True)
    print(f"sleep-log-v49 verification passed with {words} visible words")


if __name__ == "__main__":
    main()
