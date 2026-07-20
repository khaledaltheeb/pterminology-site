from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    runtime = (SITE / "assets/js/lab-v12.js").read_text(encoding="utf-8")
    index_runtime = (SITE / "assets/js/encyclopedia-v14.js").read_text(encoding="utf-8")
    service_worker = (SITE / "sw.js").read_text(encoding="utf-8")
    index = (SITE / "encyclopedia/index.html").read_text(encoding="utf-8")
    lab_page = (SITE / "assessment-lab/phq-9-plus/index.html").read_text(encoding="utf-8")

    require("MutationObserver" not in runtime, "MutationObserver loop remains in lab runtime")
    require("getComputedStyle" not in runtime, "Global computed-style scan remains in lab runtime")
    require("pterminology-v12-direct" not in service_worker, "Old v12 cache name remains")
    require("pterminology-v14-performance" in service_worker, "v14 cache name missing")
    require("skipWaiting" in service_worker, "Service worker skipWaiting missing")
    require("clients.claim" in service_worker, "Service worker clients.claim missing")
    require("PAGE_SIZE=48" in index_runtime, "Encyclopedia page size is not bounded to 48")
    require("ency-v13__card" not in index, "Static 2000-card encyclopedia DOM remains")
    require("lab-v12.js" not in index, "Lab runtime still loaded by encyclopedia index")
    require("encyclopedia-v14.js" in index, "Paginated encyclopedia runtime missing")
    require("lab-v12.js" in lab_page, "Lab runtime missing from an assessment page")

    offenders: list[str] = []
    for folder in (SITE / "encyclopedia", SITE / "hubs"):
        for page in folder.rglob("*.html"):
            if "lab-v12.js" in page.read_text(encoding="utf-8"):
                offenders.append(page.relative_to(SITE).as_posix())
                if len(offenders) >= 20:
                    break
    require(not offenders, f"Lab runtime remains on non-lab pages: {offenders}")

    performance = json.loads((SITE / "api/performance-v14.json").read_text(encoding="utf-8"))
    pwa = json.loads((SITE / "api/pwa-v14.json").read_text(encoding="utf-8"))
    integrity = json.loads((SITE / "api/site-integrity-v13.json").read_text(encoding="utf-8"))

    require(performance.get("mutation_observer_removed") is True, "Performance report: observer not removed")
    require(performance.get("computed_style_scan_removed") is True, "Performance report: style scan not removed")
    require(performance.get("no_2000_static_cards") is True, "Performance report: static cards remain")
    require(performance.get("items") == 2000, "Performance report: encyclopedia item count changed")
    require(performance.get("total_removed_lab_script_tags", 0) > 2000, "Too few non-lab runtime tags removed")
    require(performance.get("residual_lab_script_tags_non_lab") == 0, "Residual non-lab runtime tags remain")
    require(performance.get("kept_lab_script_tags_after_regex", 0) > 0, "Lab pages lost their runtime")
    require(pwa.get("old_cache_deleted") is True, "PWA report: old caches are not deleted")
    require(integrity.get("errors") == 0 and integrity.get("error_count") == 0, f"Integrity errors: {integrity}")

    result = {"performance": performance, "pwa": pwa, "integrity": integrity, "offenders": offenders}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
