from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
BRAND = "منصة الصحة النفسية وذوي الاحتياجات الخاصة"
SLOGAN = "معرفة تحترم الإنسان. دعم يوسّع الإمكانات."
REQUIRED_LINKS = (
    "start-here/",
    "encyclopedia/",
    "hubs/",
    "tips/",
    "care-guides/",
    "special-needs/",
    "assessment-lab/",
    "cognitive-lab/",
    "sectors/family/",
    "sectors/child/",
    "sectors/home/",
    "provider-assessment-demo/",
    "trust/",
    "partners/",
)


class StrictHTMLParser(HTMLParser):
    pass


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    StrictHTMLParser().feed(source)

    assert 'lang="ar"' in source and 'dir="rtl"' in source
    assert BRAND in source, "Homepage is missing the unified platform name"
    assert SLOGAN in source, "Homepage is missing the approved slogan candidate"
    assert "مصطلحات علم النفس — الاسم المؤسس" in source, "Founding name must remain visible"
    assert "ثلاثين شرحًا" not in source, "Homepage contains obsolete 30-item claim"
    assert "2000+" not in source, "Homepage must not preserve an unverified static scale claim"
    assert "هدف معلن للموسوعة النفسية العربية" in source, "10,000 must be labelled as a target, not a completed count"
    assert "هدف أدنى لكل مسار رئيسي" in source, "100+ content figures must be labelled as targets"
    assert len(re.findall(r"<h1\b", source)) == 1, "Homepage must contain exactly one h1"
    assert len(re.findall(r"<h2\b", source)) >= 4, "Homepage needs structured H2 sections"
    assert len(re.findall(r"<h3\b", source)) >= 12, "Homepage needs discoverable H3 cards"
    assert 'href="#main"' in source, "Missing skip link"
    assert 'id="main"' in source, "Missing main landmark target"
    assert 'color-scheme" content="light"' in source, "Homepage must declare light color scheme"
    assert "background:#071827" not in source and "background:#000" not in source, "Dark homepage regression"
    assert "قيد الإعداد" not in source and "قيد التوسع" not in source, "Homepage contains placeholder language"

    for link in REQUIRED_LINKS:
        assert f'href="{link}"' in source, f"Missing primary discovery link: {link}"

    description = re.search(r'<meta name="description" content="([^"]+)"', source)
    assert description and 100 <= len(description.group(1)) <= 220

    structured = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL
    )
    assert structured, "Missing JSON-LD"
    payload = json.loads(structured.group(1))
    graph = payload.get("@graph", [])
    assert any(node.get("@type") == "WebSite" and node.get("name") == BRAND for node in graph)
    assert any(node.get("@type") == "CollectionPage" for node in graph)
    assert any(node.get("@type") == "Organization" and node.get("name") == BRAND for node in graph)
    organization = next(node for node in graph if node.get("@type") == "Organization")
    assert SLOGAN == organization.get("slogan")
    assert "مصطلحات علم النفس" in organization.get("alternateName", [])

    print(
        json.dumps(
            {
                "status": "passed",
                "brand": BRAND,
                "slogan": SLOGAN,
                "required_links": len(REQUIRED_LINKS),
                "description_chars": len(description.group(1)),
                "jsonld_nodes": len(graph),
                "h1": len(re.findall(r"<h1\b", source)),
                "h2": len(re.findall(r"<h2\b", source)),
                "h3": len(re.findall(r"<h3\b", source)),
                "targets_are_labeled": True,
                "light_palette": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
