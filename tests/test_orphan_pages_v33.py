from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "scripts" / "audit_orphan_pages_v33.py"


def write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        site = Path(temp) / "_site"
        write(
            site / "index.html",
            '<a href="guide/">دليل</a><a href="https://khaledaltheeb.github.io/pterminology-site/article/?x=1#top">مقال</a>',
        )
        write(site / "guide" / "index.html", '<a href="../article/">المقال</a>')
        write(site / "article" / "index.html", '<a href="/pterminology-site/guide/index.html">الدليل</a>')
        write(site / "orphan" / "index.html", "<p>صفحة يتيمة</p>")
        write(site / "404.html", "<p>غير موجود</p>")
        write(
            site / "google-verification.html",
            "google-site-verification: google-verification.html",
        )

        subprocess.run([sys.executable, str(AUDITOR), str(site)], check=True)
        report = json.loads((site / "api" / "orphan-pages-v33.json").read_text(encoding="utf-8"))
        assert report["pages_scanned"] == 6, report
        assert report["navigable_pages"] == 5, report
        assert report["verification_pages_skipped"] == ["google-verification.html"], report
        assert report["orphan_eligible_pages"] == 3, report
        assert report["orphan_page_count"] == 1, report
        assert report["orphan_pages"] == ["orphan/index.html"], report
        counts = {item["path"]: item["inbound_internal_links"] for item in report["pages"]}
        eligibility = {item["path"]: item["orphan_eligible"] for item in report["pages"]}
        assert counts["guide/index.html"] == 2, counts
        assert counts["article/index.html"] == 2, counts
        assert counts["index.html"] == 0, counts
        assert eligibility["404.html"] is False, eligibility
        assert "google-verification.html" not in counts, counts
        assert report["unresolved_internal_target_count"] == 0, report
    print("orphan page audit v33: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
