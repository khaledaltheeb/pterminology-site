from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
SOURCE = ROOT / "index.html"
TARGET = SITE / "index.html"


def run_publisher(script: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), str(SITE)],
        check=True,
    )


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit("Missing source homepage index.html")
    if not SITE.exists():
        raise SystemExit(f"Missing site output: {SITE}")
    text = SOURCE.read_text(encoding="utf-8")
    required = [
        '<html lang="ar" dir="rtl">',
        '<h1>',
        'href="encyclopedia/"',
        'href="tips/"',
        'href="assessment-lab/"',
        'href="cognitive-lab/"',
        'href="sectors/family/"',
        'rel="manifest"',
        'application/ld+json',
        'color-scheme" content="light"',
    ]
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Homepage source missing required markers: {missing}")
    forbidden = [
        'background:linear-gradient(145deg,var(--navy),var(--navy2))',
        'background:#071827',
        'background:#000',
        'background:black',
    ]
    found = [item for item in forbidden if item in text]
    if found:
        raise SystemExit(f"Dark homepage regression detected: {found}")
    if text.count('<h1>') != 1:
        raise SystemExit(f"Expected exactly one H1, found {text.count('<h1>')}")
    if len(re.findall(r'<h2\b', text)) < 3:
        raise SystemExit("Homepage must contain at least three H2 sections")
    if len(re.findall(r'<h3\b', text)) < 6:
        raise SystemExit("Homepage must contain at least six H3 cards")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, TARGET)
    report = {
        "version": 20,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "h1": text.count('<h1>'),
        "h2": len(re.findall(r'<h2\b', text)),
        "h3": len(re.findall(r'<h3\b', text)),
        "light_palette": True,
        "core_sections_linked": True,
        "trust_center_publisher": 71,
        "homepage_i18n_publisher": 72,
        "care_guides_publisher": 73,
        "special_needs_publisher": 73,
        "women_center_publisher": 165,
    }
    if report["source_sha256"] != report["target_sha256"]:
        raise SystemExit("Homepage copy hash mismatch")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "homepage-v20.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    run_publisher("publish_trust_center_v71.py")
    run_publisher("finalize_trust_center_links_v71.py")

    # Every production-like pipeline that applies the homepage must also create
    # the care-guide destination before newer centers link to it. The linker
    # normalizes mixed sitemap roots and is designed to be idempotent.
    run_publisher("publish_care_guides_v21.py")
    run_publisher("link_care_guides_v21.py")

    run_publisher("publish_special_needs_v73.py")
    run_publisher("publish_women_center_v165.py")
    run_publisher("publish_homepage_i18n_v72.py")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
