from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
SOURCE = ROOT / "index.html"
TARGET = SITE / "index.html"
DISCOVERY_VERSION = 196
DISCOVERY_ROUTES = [
    "start-here/",
    "encyclopedia/",
    "blog/",
    "care-guides/",
    "special-needs/",
    "tips/",
    "assessment-lab/",
    "cognitive-lab/",
    "sectors/family/",
    "hubs/",
    "trust/",
]


def run_publisher(script: str) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), str(SITE)],
        check=True,
    )


def synchronize_care_guides_report() -> None:
    report_path = SITE / "api" / "care-guides-v21.json"
    sitemap_path = SITE / "sitemap-care-guides.xml"
    guide_root = SITE / "care-guides"
    expected_page = guide_root / "choosing-mental-health-professional" / "index.html"
    expected_url = "https://khaledaltheeb.github.io/pterminology-site/care-guides/choosing-mental-health-professional/"

    if not report_path.is_file():
        raise SystemExit("Missing care-guides-v21.json after guide publication")
    if not sitemap_path.is_file() or not expected_page.is_file():
        raise SystemExit("Choosing-professional guide or care-guide sitemap is missing")

    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.parse(sitemap_path).getroot()
    urls = [node.text for node in root.findall("sm:url/sm:loc", namespace) if node.text]
    if expected_url not in urls:
        raise SystemExit("Choosing-professional guide is absent from care-guide sitemap")
    if len(urls) != len(set(urls)):
        raise SystemExit("Duplicate URLs detected in care-guide sitemap")

    html_pages = sorted(guide_root.rglob("index.html"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["version"] = 178
    report["guides"] = max(int(report.get("guides", 0)), len(urls) - 1)
    report["pages"] = len(html_pages)
    report["sitemap_urls"] = len(urls)
    report["choosing_professional_guide"] = True
    report["choosing_professional_route"] = expected_url
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def register_sitemap(sitemap_name: str) -> None:
    sitemap_path = SITE / sitemap_name
    sitemap_index = SITE / "sitemap.xml"
    if not sitemap_path.is_file() or not sitemap_index.is_file():
        raise SystemExit(f"Missing sitemap integration input: {sitemap_name}")

    target = f"https://khaledaltheeb.github.io/pterminology-site/{sitemap_name}"
    tree = ET.parse(sitemap_index)
    root = tree.getroot()
    existing = [(node.text or "").strip() for node in root.findall("{*}sitemap/{*}loc")]
    if target not in existing:
        sitemap = ET.SubElement(root, "sitemap")
        ET.SubElement(sitemap, "loc").text = target
    tree.write(sitemap_index, encoding="utf-8", xml_declaration=True)

    tree = ET.parse(sitemap_index)
    current = [(node.text or "").strip() for node in tree.getroot().findall("{*}sitemap/{*}loc")]
    if current.count(target) != 1:
        raise SystemExit(f"Expected exactly one sitemap index entry for {sitemap_name}")


def validate_discovery(text: str) -> dict[str, object]:
    missing_routes = [route for route in DISCOVERY_ROUTES if f'href="{route}"' not in text]
    if missing_routes:
        raise SystemExit(f"Homepage discovery routes missing: {missing_routes}")
    if '"@type": "ItemList"' not in text or '"numberOfItems": 11' not in text:
        raise SystemExit("Homepage discovery ItemList schema is missing or incomplete")
    if "البلوج" not in text or "ذوو الاحتياجات" not in text:
        raise SystemExit("Homepage metadata and visible copy must expose blog and special-needs paths")
    generic_labels = ["اضغط هنا", ">اقرأ المزيد<", ">المزيد<"]
    found_generic = [label for label in generic_labels if label in text]
    if found_generic:
        raise SystemExit(f"Generic homepage link labels detected: {found_generic}")
    return {
        "version": DISCOVERY_VERSION,
        "status": "built-not-published",
        "routes": DISCOVERY_ROUTES,
        "route_count": len(DISCOVERY_ROUTES),
        "item_list_schema": True,
        "blog_linked": True,
        "special_needs_linked": True,
        "care_guides_linked": True,
        "start_here_linked": True,
        "trust_center_linked": True,
    }


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
        'href="blog/"',
        'href="special-needs/"',
        'href="care-guides/"',
        'href="start-here/"',
        'href="trust/"',
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
    h1_count = text.count("<h1>")
    h2_count = len(re.findall(r"<h2\b", text))
    h3_count = len(re.findall(r"<h3\b", text))
    if h1_count != 1:
        raise SystemExit(f"Expected exactly one H1, found {h1_count}")
    if h2_count < 4:
        raise SystemExit("Homepage must contain at least four H2 sections")
    if h3_count < 10:
        raise SystemExit("Homepage must contain at least ten H3 discovery cards")

    discovery_report = validate_discovery(text)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, TARGET)
    report = {
        "version": 20,
        "discovery_version": DISCOVERY_VERSION,
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "target_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "h1": h1_count,
        "h2": h2_count,
        "h3": h3_count,
        "light_palette": True,
        "core_sections_linked": True,
        "discovery_route_count": len(DISCOVERY_ROUTES),
        "blog_linked": True,
        "special_needs_linked": True,
        "care_guides_linked": True,
        "start_here_linked": True,
        "trust_center_linked": True,
        "structured_navigation": "ItemList",
        "trust_center_publisher": 71,
        "homepage_i18n_publisher": 72,
        "care_guides_publisher": 73,
        "special_needs_publisher": 73,
        "start_here_publisher": 176,
        "choose_professional_publisher": 176,
        "care_guides_report_sync": 178,
        "inclusive_disability_language_publisher": 186,
        "inclusive_disability_language_sitemap_sync": 187,
        "caregiver_wellbeing_publisher": 188,
        "caregiver_wellbeing_sitemap_sync": 189,
        "accessible_arabic_content_publisher": 190,
        "accessible_arabic_content_sitemap_sync": 191,
        "health_publication_gate": 192,
        "homepage_discovery_upgrade": DISCOVERY_VERSION,
    }
    if report["source_sha256"] != report["target_sha256"]:
        raise SystemExit("Homepage copy hash mismatch")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "homepage-v20.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (api / "homepage-discovery-v196.json").write_text(
        json.dumps(discovery_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    run_publisher("publish_trust_center_v71.py")
    run_publisher("finalize_trust_center_links_v71.py")

    run_publisher("publish_care_guides_v21.py")
    run_publisher("link_care_guides_v21.py")

    run_publisher("publish_special_needs_v73.py")
    run_publisher("publish_choose_professional_v176.py")
    synchronize_care_guides_report()
    run_publisher("publish_homepage_i18n_v72.py")
    run_publisher("publish_start_here_v176.py")
    run_publisher("publish_inclusive_disability_language_v186.py")
    register_sitemap("sitemap-inclusive-disability-language.xml")
    run_publisher("publish_caregiver_wellbeing_v188.py")
    register_sitemap("sitemap-caregiver-wellbeing.xml")
    run_publisher("publish_accessible_arabic_content_v190.py")
    register_sitemap("sitemap-accessible-arabic-content.xml")
    run_publisher("enforce_health_publication_gate_v192.py")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
