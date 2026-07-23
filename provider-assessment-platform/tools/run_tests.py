#!/usr/bin/env python3
"""Run provider-assessment tests against the strict runtime implementation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import runtime  # noqa: E402

# Existing tests import engine.rules. Route that import to the strict public
# runtime so all suites exercise the production tri-state behavior.
sys.modules["engine.rules"] = runtime


def main() -> int:
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(ROOT / "tests"),
        pattern="test_*.py",
        top_level_dir=str(ROOT),
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
