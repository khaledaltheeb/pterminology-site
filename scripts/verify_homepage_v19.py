from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
REQUIRED_LINKS = (
    "encyclopedia/",
    "hubs/",
    "tips/",
    "assessment-lab/",
    "cognitive-lab/",
    "sectors/family/",
)


class StrictHTMLParser(HTMLParser):
    pass


def main() -> None:
    source = INDEX.read_text(encoding="utf-8")
    StrictHTMLParser().feed(source)

    assert 'lang="ar"' in source and 'dir="rtl"' in source
    assert "ثلاثين شرحًا" not in source, "Homepage contains obsolete 30-item claim"
    assert "2000+" in source, "Homepage does not communicate the current encyclopedia scale"
    assert len(re.findall(r"<h1\b", source)) == 1, "Homepage must contain exactly one h1"
    assert len(re.findall(r"<h2\b", source)) >= 3, "Homepage needs structured H2 sections"
    assert len(re.findall(r"<h3\b", source)) >= 6, "Homepage needs discoverable H3 cards"
    assert 'href="#main"' in source, "Missing skip link"
    assert 'id="main"' in source, "Missing main landmark target"
    assert 'color-scheme" content="light"' in source, "Homepage must declare light color scheme"
    assert "background:#071827" not in source and "background:#000" not in source, "Dark homepage regression"

    for link in REQUIRED_LINKS:
        assert f'href="{link}"' in source, f"Missing primary discovery link: {link}"

    description = re.search(r'<meta name="description" content="([^"]+)"', source)
    assert description and 100 <= len(description.group(1)) <= 240

    structured = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', source, re.DOTALL
    )
    assert structured, "Missing JSON-LD"
    payload = json.loads(structured.group(1))
    graph = payload.get("@graph", [])
    assert any(node.get("@type") == "WebSite" for node in graph)
    assert any(node.get("@type") == "CollectionPage" for node in graph)
    assert any(node.get("@type") == "Organization" for node in graph)

    print(
        json.dumps(
            {
                "status": "passed",
                "required_links": len(REQUIRED_LINKS),
                "description_chars": len(description.group(1)),
                "jsonld_nodes": len(graph),
                "h1": len(re.findall(r"<h1\b", source)),
                "h2": len(re.findall(r"<h2\b", source)),
                "h3": len(re.findall(r"<h3\b", source)),
                "light_palette": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
