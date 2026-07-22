from __future__ import annotations

import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "daily-tools" / "sleep-wind-down-plan" / "index.html"


def patch() -> None:
    """Validate the generated shell without duplicating JS-managed controls.

    The SVG export button and its privacy disclosure are intentionally created by
    sleep-log-v49.js so they remain bound to the same tested runtime. This step
    protects production builds from stale static copies or duplicate element IDs.
    """
    if not PAGE.is_file():
        raise SystemExit(f"Missing generated sleep page: {PAGE}")

    text = PAGE.read_text(encoding="utf-8")
    if "sleep-log-v49.js" not in text:
        raise SystemExit("Generated sleep page does not load sleep-log-v49.js")

    stale_markers = (
        'data-export-svg',
        'id="sleep-svg-export-privacy"',
    )
    if any(marker in text for marker in stale_markers):
        raise SystemExit("Stale static SVG export markup would duplicate JS-managed controls")


if __name__ == "__main__":
    patch()
