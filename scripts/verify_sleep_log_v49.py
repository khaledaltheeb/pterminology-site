from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(text: str, pattern: str, message: str) -> None:
    if not re.search(pattern, text, re.I | re.S):
        raise AssertionError(message)


def main() -> None:
    # The repository checkout already contains the production site artifact used
    # by the incremental publishers.  Do not call the removed v15 full-site
    # publisher: doing so makes this verifier depend on an obsolete file and
    # fail before the tool-specific build can run.
    site = ROOT / '_site'
    sitemap = site / 'sitemap.xml'
    if not site.is_dir() or not sitemap.is_file():
        raise AssertionError('production site artifact or sitemap.xml missing')

    subprocess.run([sys.executable, str(ROOT / 'scripts/publish_daily_tools_v24.py')], check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/publish_sleep_log_v49.py')], check=True)
    page = ROOT / '_site/daily-tools/sleep-wind-down-plan/index.html'
    text = page.read_text(encoding='utf-8')
    js = (ROOT / 'assets/sleep-log-v49.js').read_text(encoding='utf-8')
    require(text, r'<html[^>]+lang="ar"[^>]+dir="rtl"', 'Arabic RTL root missing')
    require(text, r'data-sleep-log', 'interactive form missing')
    require(text, r'role="status"[^>]+aria-live="polite"', 'live status missing')
    require(text, r'غير تشخيص', 'non-diagnostic boundary missing')
    require(text, r'لا تُرسل البيانات إلى خادم', 'local privacy statement missing')
    require(text, r'data-delete-sleep', 'delete-all control missing')
    require(text, r'data-export-json', 'JSON export missing')
    require(text, r'data-export-csv', 'CSV export missing')
    require(text, r'data-print-sleep', 'print control missing')
    require(text, r'prefers-reduced-motion', 'reduced motion support missing')
    require(text, r'@media print', 'print stylesheet missing')
    require(text, r'min-height:44px', 'touch target baseline missing')
    require(text, r'خدمات الطوارئ المحلية', 'urgent-help route missing')
    for field in ('date', 'bedtime', 'wakeTime', 'quality', 'energy', 'note'):
        require(text, rf'name="{field}"[^>]+aria-describedby="[^"]+"', f'{field} must reference its error message')
        require(text, rf'data-field-error="{field}"', f'{field} error container missing')
    require(js, r"setAttribute\('aria-invalid',\s*'true'\)", 'invalid fields must expose aria-invalid')
    require(js, r'firstInvalid\.focus\(\)', 'focus must move to the first invalid field')
    require(js, r'data-field-error', 'field error rendering missing')
    if 'fetch(' in js:
        raise AssertionError('network transmission is not allowed')
    subprocess.run(['node', str(ROOT / 'tests/test_sleep_log_v49.mjs')], check=True)
    print('sleep-log-v49 verification passed')


if __name__ == '__main__':
    main()
