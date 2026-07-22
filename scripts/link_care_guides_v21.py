from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
PAGE = SITE / "index.html"
FAMILY_PAGE = SITE / "sectors" / "family" / "index.html"
ENCYCLOPEDIA_PAGE = SITE / "encyclopedia" / "index.html"
ADHD_PAGE = SITE / "care-guides" / "adhd-family-practical-guide" / "index.html"

NAV_MARKER = '<a href="tips/">النصائح</a>'
NAV_LINK = '<a href="care-guides/">أدلة التعامل</a>'
ACTION_MARKER = '<a class="btn secondary" href="tips/">افتح الأدلة العملية</a>'
ACTION_LINK = '<a class="btn secondary" href="care-guides/">أدلة التعامل مع الحالات</a>'

ADHD_HREF = "/pterminology-site/care-guides/adhd-family-practical-guide/"
FAMILY_ADHD_BLOCK = f'''<!-- adhd-family-journey-v42 -->
<section class="care-v21__section" aria-labelledby="adhd-family-guide-link">
  <h2 id="adhd-family-guide-link">دعم الأسرة مع اضطراب نقص الانتباه وفرط النشاط</h2>
  <p>انتقل من فهم الحالة إلى خطة عملية للمنزل والمدرسة والواجبات والنوم، مع حدود واضحة لطلب المساعدة المهنية.</p>
  <p><a href="{ADHD_HREF}">اقرأ دليل الأسرة العملي لاضطراب نقص الانتباه وفرط النشاط</a></p>
</section>
<!-- /adhd-family-journey-v42 -->'''
ENCYCLOPEDIA_ADHD_BLOCK = f'''<!-- adhd-encyclopedia-journey-v42 -->
<section class="ency-v13__section" aria-labelledby="adhd-practical-guide-link">
  <h2 id="adhd-practical-guide-link">بعد قراءة مصطلحات ADHD</h2>
  <p>للتطبيق الأسري والمدرسي المنظم، استخدم الدليل العملي غير التشخيصي المرتبط بالحالة.</p>
  <p><a href="{ADHD_HREF}">افتح دليل الأسرة العملي لـ ADHD</a></p>
</section>
<!-- /adhd-encyclopedia-journey-v42 -->'''
ADHD_RELATED_BLOCK = '''<!-- adhd-related-journey-v42 -->
<section class="care-v21__section" aria-labelledby="adhd-related-links">
  <h2 id="adhd-related-links">أكمل رحلة الفهم والدعم</h2>
  <ul>
    <li><a href="/pterminology-site/care-guides/">تصفح مكتبة أدلة التعامل والأسرة</a></li>
    <li><a href="/pterminology-site/sectors/family/">انتقل إلى مركز الأسرة ومسارات الدعم</a></li>
    <li><a href="/pterminology-site/encyclopedia/?q=ADHD">راجع مصطلحات ADHD والفروق المرتبطة في الموسوعة</a></li>
  </ul>
  <p>هذه الروابط للتثقيف والتنظيم ولا تحول الدليل أو نتائج البحث إلى تشخيص.</p>
</section>
<!-- /adhd-related-journey-v42 -->'''


def inject_once(text: str, marker: str, link: str, label: str) -> str:
    if link in text:
        return text
    if marker not in text:
        raise SystemExit(f"Homepage {label} marker changed; refusing unsafe care-guide injection")
    return text.replace(marker, marker + link, 1)


def inject_before_main(path: Path, block: str, marker: str, label: str) -> bool:
    if not path.exists():
        raise SystemExit(f"Missing {label} page: {path.relative_to(SITE)}")
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return False
    if "</main>" not in text:
        raise SystemExit(f"{label} page has no </main>; refusing unsafe injection")
    path.write_text(text.replace("</main>", block + "</main>", 1), encoding="utf-8")
    return True


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def qualify(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0] + "}" + name
    return name


def normalize_main_sitemap() -> dict[str, object]:
    main_path = SITE / "sitemap.xml"
    care_path = SITE / "sitemap-care-guides.xml"
    if not main_path.exists() or not care_path.exists():
        raise SystemExit("Main or care-guide sitemap is missing")

    main_tree = ET.parse(main_path)
    main_root = main_tree.getroot()
    root_type = local_name(main_root.tag)
    care_tree = ET.parse(care_path)
    care_urls = [
        node.text.strip()
        for node in care_tree.getroot().findall("{*}url/{*}loc")
        if node.text and node.text.strip()
    ]
    if not care_urls:
        raise SystemExit("Care-guide sitemap contains no URLs")

    changed = False
    if root_type == "urlset":
        invalid_children = [child for child in list(main_root) if local_name(child.tag) == "sitemap"]
        for child in invalid_children:
            main_root.remove(child)
            changed = True
        existing = {
            node.text.strip()
            for node in main_root.findall("{*}url/{*}loc")
            if node.text and node.text.strip()
        }
        url_tag = qualify(main_root, "url")
        loc_tag = qualify(main_root, "loc")
        for url in care_urls:
            if url in existing:
                continue
            item = ET.SubElement(main_root, url_tag)
            ET.SubElement(item, loc_tag).text = url
            existing.add(url)
            changed = True
    elif root_type == "sitemapindex":
        invalid_children = [child for child in list(main_root) if local_name(child.tag) == "url"]
        for child in invalid_children:
            main_root.remove(child)
            changed = True
        target = "https://khaledaltheeb.github.io/pterminology-site/sitemap-care-guides.xml"
        existing = {
            node.text.strip()
            for node in main_root.findall("{*}sitemap/{*}loc")
            if node.text and node.text.strip()
        }
        if target not in existing:
            sitemap = ET.SubElement(main_root, qualify(main_root, "sitemap"))
            ET.SubElement(sitemap, qualify(main_root, "loc")).text = target
            changed = True
    else:
        raise SystemExit(f"Unsupported sitemap root: {root_type}")

    if changed:
        main_tree.write(main_path, encoding="utf-8", xml_declaration=True)

    reparsed = ET.parse(main_path).getroot()
    valid = local_name(reparsed.tag) in {"urlset", "sitemapindex"}
    if local_name(reparsed.tag) == "urlset":
        valid = valid and not any(local_name(child.tag) == "sitemap" for child in reparsed)
    else:
        valid = valid and not any(local_name(child.tag) == "url" for child in reparsed)
    if not valid:
        raise SystemExit("Main sitemap mixes urlset and sitemapindex element contracts")
    return {"root_type": local_name(reparsed.tag), "changed": changed, "valid": valid}


def main() -> None:
    if not PAGE.exists():
        raise SystemExit("Production homepage is missing")

    text = PAGE.read_text(encoding="utf-8")
    text = inject_once(text, NAV_MARKER, NAV_LINK, "navigation")
    text = inject_once(text, ACTION_MARKER, ACTION_LINK, "hero action")

    if text.count(NAV_LINK) != 1 or text.count(ACTION_LINK) != 1:
        raise SystemExit("Care-guide links must each appear exactly once")

    PAGE.write_text(text, encoding="utf-8")
    family_changed = inject_before_main(
        FAMILY_PAGE, FAMILY_ADHD_BLOCK, "adhd-family-journey-v42", "family hub"
    )
    encyclopedia_changed = inject_before_main(
        ENCYCLOPEDIA_PAGE,
        ENCYCLOPEDIA_ADHD_BLOCK,
        "adhd-encyclopedia-journey-v42",
        "encyclopedia hub",
    )
    target_changed = inject_before_main(
        ADHD_PAGE, ADHD_RELATED_BLOCK, "adhd-related-journey-v42", "ADHD guide"
    )
    sitemap_state = normalize_main_sitemap()

    family_text = FAMILY_PAGE.read_text(encoding="utf-8")
    encyclopedia_text = ENCYCLOPEDIA_PAGE.read_text(encoding="utf-8")
    target_text = ADHD_PAGE.read_text(encoding="utf-8")
    report = {
        "version": 43,
        "care_guides_linked": text.count('href="care-guides/"') >= 2,
        "navigation_link": NAV_LINK in text,
        "hero_link": ACTION_LINK in text,
        "duplicate_free": text.count(NAV_LINK) == 1 and text.count(ACTION_LINK) == 1,
        "adhd_inbound_from_care_hub": ADHD_HREF in (SITE / "care-guides" / "index.html").read_text(encoding="utf-8"),
        "adhd_inbound_from_family_hub": ADHD_HREF in family_text,
        "adhd_inbound_from_encyclopedia_hub": ADHD_HREF in encyclopedia_text,
        "adhd_outgoing_to_care_hub": "/pterminology-site/care-guides/" in target_text,
        "adhd_outgoing_to_family_hub": "/pterminology-site/sectors/family/" in target_text,
        "adhd_outgoing_to_encyclopedia_search": "/pterminology-site/encyclopedia/?q=ADHD" in target_text,
        "idempotent_blocks": family_text.count("adhd-family-journey-v42") == 2
        and encyclopedia_text.count("adhd-encyclopedia-journey-v42") == 2
        and target_text.count("adhd-related-journey-v42") == 2,
        "main_sitemap_valid": bool(sitemap_state["valid"]),
        "main_sitemap_root": sitemap_state["root_type"],
        "changed": {
            "family_hub": family_changed,
            "encyclopedia_hub": encyclopedia_changed,
            "adhd_guide": target_changed,
            "sitemap": sitemap_state["changed"],
        },
    }
    required = [
        key
        for key in report
        if key not in {"version", "changed", "main_sitemap_root"}
    ]
    if not all(report[key] for key in required):
        raise SystemExit(f"Care-guide journey integration failed: {report}")

    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "care-guides-homepage-v21.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
