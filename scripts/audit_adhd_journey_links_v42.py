from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
BASE_PATH = "/pterminology-site/"
TARGET = "care-guides/adhd-family-practical-guide/index.html"
TARGET_HREF = f"{BASE_PATH}care-guides/adhd-family-practical-guide/"


def read(rel: str) -> str:
    path = SITE / rel
    if not path.exists():
        raise SystemExit(f"Missing required page: {rel}")
    return path.read_text(encoding="utf-8", errors="strict")


def main() -> int:
    target_html = read(TARGET)
    required_sources = {
        "care_hub": "care-guides/index.html",
        "family_hub": "sectors/family/index.html",
        "encyclopedia_hub": "encyclopedia/index.html",
    }
    inbound: dict[str, bool] = {}
    for name, rel in required_sources.items():
        inbound[name] = TARGET_HREF in read(rel)

    outgoing_destinations = {
        "care_hub": f'{BASE_PATH}care-guides/',
        "family_hub": f'{BASE_PATH}sectors/family/',
        "encyclopedia_search": f'{BASE_PATH}encyclopedia/?q=ADHD',
    }
    outgoing = {name: href in target_html for name, href in outgoing_destinations.items()}

    canonical = re.search(r'<link rel="canonical" href="([^"]+)"', target_html)
    breadcrumb = "BreadcrumbList" in target_html
    schema_article = any(token in target_html for token in ('"@type": "Article"', '"@type":"Article"', '"@type": "MedicalWebPage"', '"@type":"MedicalWebPage"'))
    sitemap = read("sitemap-care-guides.xml")
    sitemap_main = read("sitemap.xml")

    checks = {
        "target_exists": True,
        "inbound_from_care_hub": inbound["care_hub"],
        "inbound_from_family_hub": inbound["family_hub"],
        "inbound_from_encyclopedia_hub": inbound["encyclopedia_hub"],
        "outgoing_to_care_hub": outgoing["care_hub"],
        "outgoing_to_family_hub": outgoing["family_hub"],
        "outgoing_to_encyclopedia_search": outgoing["encyclopedia_search"],
        "self_canonical": bool(canonical and canonical.group(1).endswith("/care-guides/adhd-family-practical-guide/")),
        "breadcrumb_schema": breadcrumb,
        "article_schema": schema_article,
        "specialized_sitemap": "care-guides/adhd-family-practical-guide/" in sitemap,
        "main_sitemap_references_care_guides": "sitemap-care-guides.xml" in sitemap_main,
    }
    failed = [name for name, ok in checks.items() if not ok]
    report = {
        "version": 42,
        "target": TARGET_HREF,
        "checks": checks,
        "failed_checks": failed,
        "required_inbound_links": 3,
        "actual_inbound_links": sum(inbound.values()),
        "required_outgoing_links": 3,
        "actual_outgoing_links": sum(outgoing.values()),
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "adhd-journey-links-v42.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if failed:
        raise SystemExit("ADHD journey link contract failed: " + ", ".join(failed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
