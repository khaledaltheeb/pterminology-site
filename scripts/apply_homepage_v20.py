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
SITE_ORIGIN = "https://khaledaltheeb.github.io/pterminology-site/"


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
    expected_url = f"{SITE_ORIGIN}care-guides/choosing-mental-health-professional/"

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


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def register_sitemap(sitemap_name: str) -> dict[str, object]:
    sitemap_path = SITE / sitemap_name
    main_path = SITE / "sitemap.xml"
    if not sitemap_path.is_file() or not main_path.is_file():
        raise SystemExit(f"Missing sitemap integration input: {sitemap_name}")

    child_tree = ET.parse(sitemap_path)
    child_root = child_tree.getroot()
    if local_name(child_root.tag) != "urlset":
        raise SystemExit(f"Child sitemap must be urlset: {sitemap_name}")
    child_urls = [
        node.text.strip()
        for node in child_root.findall("{*}url/{*}loc")
        if node.text and node.text.strip()
    ]
    if not child_urls or len(child_urls) != len(set(child_urls)):
        raise SystemExit(f"Child sitemap has no URLs or contains duplicates: {sitemap_name}")

    main_tree = ET.parse(main_path)
    main_root = main_tree.getroot()
    root_type = local_name(main_root.tag)
    changed = False

    if root_type == "urlset":
        for child in [node for node in list(main_root) if local_name(node.tag) == "sitemap"]:
            main_root.remove(child)
            changed = True

        existing = {
            node.text.strip()
            for node in main_root.findall("{*}url/{*}loc")
            if node.text and node.text.strip()
        }
        for url in child_urls:
            if url in existing:
                continue
            item = ET.SubElement(main_root, qualify(main_root, "url"))
            ET.SubElement(item, qualify(main_root, "loc")).text = url
            existing.add(url)
            changed = True
    elif root_type == "sitemapindex":
        for child in [node for node in list(main_root) if local_name(node.tag) == "url"]:
            main_root.remove(child)
            changed = True

        target = f"{SITE_ORIGIN}{sitemap_name}"
        existing = {
            node.text.strip()
            for node in main_root.findall("{*}sitemap/{*}loc")
            if node.text and node.text.strip()
        }
        if target not in existing:
            item = ET.SubElement(main_root, qualify(main_root, "sitemap"))
            ET.SubElement(item, qualify(main_root, "loc")).text = target
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {root_type}")

    if changed:
        main_tree.write(main_path, encoding="utf-8", xml_declaration=True)

    reparsed = ET.parse(main_path).getroot()
    reparsed_type = local_name(reparsed.tag)
    valid = reparsed_type in {"urlset", "sitemapindex"}
    if reparsed_type == "urlset":
        valid = valid and not any(local_name(child.tag) == "sitemap" for child in reparsed)
        current_urls = [
            node.text.strip()
            for node in reparsed.findall("{*}url/{*}loc")
            if node.text and node.text.strip()
        ]
        valid = valid and all(current_urls.count(url) == 1 for url in child_urls)
    elif reparsed_type == "sitemapindex":
        valid = valid and not any(local_name(child.tag) == "url" for child in reparsed)
        target = f"{SITE_ORIGIN}{sitemap_name}"
        current_maps = [
            node.text.strip()
            for node in reparsed.findall("{*}sitemap/{*}loc")
            if node.text and node.text.strip()
        ]
        valid = valid and current_maps.count(target) == 1

    if not valid:
        raise SystemExit(f"Main sitemap contract invalid after registering {sitemap_name}")

    return {
        "root_type": reparsed_type,
        "changed": changed,
        "valid": valid,
        "registered_urls": len(child_urls),
    }


def publish_static_partners() -> dict[str, object]:
    source_root = ROOT / "partners"
    source_page = source_root / "index.html"
    source_registry = source_root / "registry.json"
    target_root = SITE / "partners"
    target_page = target_root / "index.html"
    target_registry = target_root / "registry.json"

    if not source_page.is_file() or not source_registry.is_file():
        raise SystemExit("Partners source page or registry is missing")

    page_text = source_page.read_text(encoding="utf-8")
    required_markers = [
        '<html lang="ar" dir="rtl">',
        '<h1>',
        'application/ld+json',
        'لا توجد حاليًا شراكات أو منح معلنة',
    ]
    missing = [marker for marker in required_markers if marker not in page_text]
    if missing:
        raise SystemExit(f"Partners page missing required governance markers: {missing}")
    if page_text.count("<h1") != 1:
        raise SystemExit("Partners page must contain exactly one H1")

    registry = json.loads(source_registry.read_text(encoding="utf-8"))
    if registry.get("entries") not in ([], None):
        raise SystemExit("Partners registry must default to no declared relationships")

    target_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_page, target_page)
    shutil.copy2(source_registry, target_registry)

    if hashlib.sha256(source_page.read_bytes()).hexdigest() != hashlib.sha256(target_page.read_bytes()).hexdigest():
        raise SystemExit("Partners page copy hash mismatch")
    if hashlib.sha256(source_registry.read_bytes()).hexdigest() != hashlib.sha256(target_registry.read_bytes()).hexdigest():
        raise SystemExit("Partners registry copy hash mismatch")

    sitemap_name = "sitemap-partners.xml"
    sitemap_path = SITE / sitemap_name
    sitemap_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f'  <url><loc>{SITE_ORIGIN}partners/</loc></url>\n'
        '</urlset>\n',
        encoding="utf-8",
    )
    sitemap_state = register_sitemap(sitemap_name)

    return {
        "page": "partners/index.html",
        "registry": "partners/registry.json",
        "declared_relationships": len(registry.get("entries") or []),
        "sitemap": sitemap_name,
        "main_sitemap_root": sitemap_state["root_type"],
        "main_sitemap_valid": sitemap_state["valid"],
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
        "internal_base_path_normalizer": 198,
        "partners_publisher": 199,
    }
    if report["source_sha256"] != report["target_sha256"]:
        raise SystemExit("Homepage copy hash mismatch")
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)

    report["partners"] = publish_static_partners()
    (api / "homepage-v20.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

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
