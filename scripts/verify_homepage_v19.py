from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
REQUIRED_LINKS = ("encyclopedia/", "terms/", "hubs/", "sitemap.xml")


class StrictHTMLParser(HTMLParser):
    pass


def main() -> None:
    html = INDEX.read_text(encoding="utf-8")
    StrictHTMLParser().feed(html)

    assert 'lang="ar"' in html and 'dir="rtl"' in html
    assert "ثلاثين شرحًا" not in html, "Homepage contains obsolete 30-item claim"
    assert "2000+" in html, "Homepage does not communicate the current encyclopedia scale"
    assert len(re.findall(r"<h1\b", html)) == 1, "Homepage must contain exactly one h1"
    assert 'href="#main"' in html, "Missing skip link"
    assert 'id="main"' in html, "Missing main landmark target"

    for link in REQUIRED_LINKS:
        assert f'href="{link}"' in html, f"Missing primary discovery link: {link}"

    description = re.search(r'<meta name="description" content="([^"]+)"', html)
    assert description and 100 <= len(description.group(1)) <= 220

    structured = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    assert structured, "Missing JSON-LD"
    payload = json.loads(structured.group(1))
    graph = payload.get("@graph", [])
    assert any(node.get("@type") == "WebSite" for node in graph)
    assert any(node.get("@type") == "CollectionPage" for node in graph)

    print(
        json.dumps(
            {
                "status": "passed",
                "required_links": len(REQUIRED_LINKS),
                "description_chars": len(description.group(1)),
                "jsonld_nodes": len(graph),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
