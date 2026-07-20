from __future__ import annotations

import json
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site").resolve()
REPORT = Path(sys.argv[2] if len(sys.argv) > 2 else SITE / "api" / "full-site-audit-v16.json").resolve()
VERIFY = "google644f1f7a8b7aaa2b.html"


class SignalParser(HTMLParser):
    """Audit real accessible link names and real script loading semantics.

    HTMLParser stores boolean attributes such as ``defer`` as ``None``. Testing
    their value therefore produces false positives; presence in the attribute
    mapping is the correct check.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.scripts: list[dict[str, str | None]] = []
        self.links: list[dict[str, object]] = []
        self._anchor_stack: list[dict[str, object]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "script" and data.get("src"):
            self.scripts.append(data)
        if tag == "a":
            self._anchor_stack.append({"attrs": data, "text": [], "image_alts": []})
        elif self._anchor_stack and tag == "img":
            alt = data.get("alt")
            if alt is not None:
                self._anchor_stack[-1]["image_alts"].append(str(alt).strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_stack:
            self.links.append(self._anchor_stack.pop())

    def handle_data(self, data: str) -> None:
        if self._anchor_stack and data.strip():
            self._anchor_stack[-1]["text"].append(data.strip())


def accessible_link_name(link: dict[str, object]) -> str:
    attrs = link["attrs"]
    assert isinstance(attrs, dict)
    for key in ("aria-label", "title"):
        value = attrs.get(key)
        if value and str(value).strip():
            return str(value).strip()
    text = " ".join(str(x) for x in link["text"]).strip()
    if text:
        return text
    return " ".join(str(x) for x in link["image_alts"] if str(x).strip()).strip()


def main() -> int:
    if not SITE.exists():
        raise SystemExit(f"Missing site directory: {SITE}")
    if not REPORT.exists():
        raise SystemExit(f"Missing v16 audit report: {REPORT}")

    actual_blocking: list[dict[str, str]] = []
    inaccessible_links: list[dict[str, str]] = []
    script_modes: Counter[str] = Counter()
    scanned_pages = 0

    for page in sorted(SITE.rglob("*.html")):
        if page.name == VERIFY:
            continue
        rel = page.relative_to(SITE).as_posix()
        parser = SignalParser()
        parser.feed(page.read_text(encoding="utf-8", errors="strict"))
        scanned_pages += 1

        for script in parser.scripts:
            src = str(script.get("src", ""))
            script_type = str(script.get("type", "")).lower()
            if script_type == "module":
                script_modes["module"] += 1
            elif "defer" in script:
                script_modes["defer"] += 1
            elif "async" in script:
                script_modes["async"] += 1
            else:
                script_modes["blocking"] += 1
                actual_blocking.append({"page": rel, "src": src})

        for link in parser.links:
            attrs = link["attrs"]
            assert isinstance(attrs, dict)
            href = str(attrs.get("href", ""))
            if href and not accessible_link_name(link):
                inaccessible_links.append({"page": rel, "href": href})

    previous = json.loads(REPORT.read_text(encoding="utf-8"))
    previous_blocking = int(previous.get("blocking_scripts", 0))
    previous_empty = int(previous.get("empty_links", 0))

    output = {
        "version": 17,
        "scanned_pages": scanned_pages,
        "script_modes": dict(script_modes),
        "actual_blocking_scripts": len(actual_blocking),
        "inaccessible_links": len(inaccessible_links),
        "v16_reported_blocking_scripts": previous_blocking,
        "v16_reported_empty_links": previous_empty,
        "corrected_false_positive_blocking_scripts": max(0, previous_blocking - len(actual_blocking)),
        "corrected_false_positive_empty_links": max(0, previous_empty - len(inaccessible_links)),
        "blocking_examples": actual_blocking[:100],
        "inaccessible_link_examples": inaccessible_links[:100],
        "errors": [],
    }

    if actual_blocking:
        output["errors"].append(f"Found {len(actual_blocking)} genuinely render-blocking external scripts")
    if inaccessible_links:
        output["errors"].append(f"Found {len(inaccessible_links)} links without an accessible name")

    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    target = api / "audit-signal-v17.json"
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))

    if output["errors"]:
        raise SystemExit("\n".join(output["errors"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
