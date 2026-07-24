#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import publish_special_needs_guides_v209 as publisher

ORIGINAL_UPSERT = publisher.upsert_urlset
MAIN_SITEMAP_MODE = "urlset"


def compatible_upsert(path: Path, urls: list[str], modified: str) -> None:
    global MAIN_SITEMAP_MODE
    if path.name != "sitemap.xml" or not path.is_file():
        ORIGINAL_UPSERT(path, urls, modified)
        return

    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", ns)
    tree = ET.parse(path)
    root = tree.getroot()
    mode = root.tag.rsplit("}", 1)[-1]
    MAIN_SITEMAP_MODE = mode

    if mode == "urlset":
        ORIGINAL_UPSERT(path, urls, modified)
        return
    if mode != "sitemapindex":
        raise SystemExit(f"Unsupported main sitemap root: {mode}")

    child_url = f"{publisher.BASE}/sitemap-special-needs.xml"
    existing = {
        node.text
        for node in root.findall(f"{{{ns}}}sitemap/{{{ns}}}loc")
        if node.text
    }
    if child_url not in existing:
        node = ET.SubElement(root, f"{{{ns}}}sitemap")
        ET.SubElement(node, f"{{{ns}}}loc").text = child_url
        ET.SubElement(node, f"{{{ns}}}lastmod").text = modified
        tree.write(path, encoding="utf-8", xml_declaration=True)


def publish(site: Path) -> dict[str, Any]:
    global MAIN_SITEMAP_MODE
    MAIN_SITEMAP_MODE = "urlset"
    publisher.upsert_urlset = compatible_upsert
    try:
        report = publisher.publish(site)
    finally:
        publisher.upsert_urlset = ORIGINAL_UPSERT

    report["main_sitemap_mode"] = MAIN_SITEMAP_MODE
    report_path = site / "api" / "special-needs-guides-v209.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    if not site.is_dir():
        raise SystemExit(f"Missing site directory: {site}")
    print(json.dumps(publish(site), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
