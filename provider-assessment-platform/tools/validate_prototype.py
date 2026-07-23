#!/usr/bin/env python3
"""Static safety and accessibility checks for the isolated provider prototype."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOTYPE = ROOT / "prototype"


class PrototypeFailure(RuntimeError):
    pass


class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.ids: set[str] = set()
        self.h1_count = 0
        self.title_text: list[str] = []
        self._in_title = False
        self.labels_for: set[str] = set()
        self.controls: list[tuple[str, dict[str, str]]] = []
        self.links: list[dict[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.stylesheets: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        self.tags.append((tag, values))
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "h1":
            self.h1_count += 1
        if tag == "title":
            self._in_title = True
        if tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])
        if tag in {"input", "textarea", "select", "button"}:
            self.controls.append((tag, values))
        if tag == "a":
            self.links.append(values)
        if tag == "script":
            self.scripts.append(values)
        if tag == "link" and "stylesheet" in values.get("rel", "").split():
            self.stylesheets.append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_text.append(data)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PrototypeFailure(message)


def is_external(value: str) -> bool:
    return value.startswith(("http://", "https://", "//"))


def validate_html(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    parser = AuditParser()
    parser.feed(content)

    html = next((attrs for tag, attrs in parser.tags if tag == "html"), None)
    require(html is not None, "Prototype must contain an html element")
    require(html.get("lang") == "ar", "Prototype language must be Arabic")
    require(html.get("dir") == "rtl", "Prototype must use RTL direction")
    require(parser.h1_count == 1, f"Prototype must contain exactly one H1, found {parser.h1_count}")
    require("".join(parser.title_text).strip(), "Prototype title is required")
    require("main-content" in parser.ids, "Skip-link target #main-content is missing")

    skip = next((link for link in parser.links if "skip-link" in link.get("class", "").split()), None)
    require(skip is not None and skip.get("href") == "#main-content", "Accessible skip link is required")

    robots = next(
        (
            attrs
            for tag, attrs in parser.tags
            if tag == "meta" and attrs.get("name", "").lower() == "robots"
        ),
        None,
    )
    require(robots is not None, "Prototype must explicitly block indexing")
    robots_tokens = {token.strip().lower() for token in robots.get("content", "").split(",")}
    require({"noindex", "nofollow"}.issubset(robots_tokens), "Prototype robots policy must be noindex,nofollow")

    require("بيانات صناعية" in content, "Synthetic-data warning is required")
    require("غير مخصصة للاستخدام السريري" in content, "Non-clinical warning is required")
    require("بوابة السلامة" in content, "Visible safety gate is required")

    for tag, attrs in parser.tags:
        inline_events = sorted(name for name in attrs if name.lower().startswith("on"))
        require(not inline_events, f"Inline event handlers are prohibited on <{tag}>: {inline_events}")

    for attrs in parser.scripts:
        source = attrs.get("src", "")
        require(source and not is_external(source), "Scripts must be local files")
        require("defer" in attrs, "Prototype script must use defer")

    for attrs in parser.stylesheets:
        href = attrs.get("href", "")
        require(href and not is_external(href), "Stylesheets must be local files")

    for attrs in parser.links:
        href = attrs.get("href", "")
        require(not href.lower().startswith("javascript:"), "javascript: links are prohibited")

    input_ids = {attrs.get("id") for tag, attrs in parser.controls if tag in {"input", "textarea", "select"} and attrs.get("id")}
    for control_id in input_ids:
        control_pattern = re.compile(
            rf"<label\b[^>]*\bfor=[\"']{re.escape(control_id)}[\"']",
            flags=re.IGNORECASE,
        )
        nested_pattern = re.compile(
            rf"<label\b[^>]*>[^<]*(?:<[^>]+>[^<]*)*<(?:input|textarea|select)\b[^>]*\bid=[\"']{re.escape(control_id)}[\"']",
            flags=re.IGNORECASE | re.DOTALL,
        )
        require(
            control_id in parser.labels_for or control_pattern.search(content) or nested_pattern.search(content),
            f"Form control #{control_id} must have a label",
        )

    for tag, attrs in parser.controls:
        if tag == "button":
            require(attrs.get("type") or attrs.get("value"), "Every button must declare type or dialog value")


def validate_css(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    required_tokens = [
        ":focus-visible",
        ".skip-link",
        "prefers-reduced-motion",
        "@media print",
        ".high-contrast",
    ]
    for token in required_tokens:
        require(token in content, f"Stylesheet is missing accessibility feature: {token}")
    require("outline: none" not in content.lower(), "Focus outlines must not be removed")


def validate_javascript(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    prohibited = {
        "fetch(": "network fetch",
        "XMLHttpRequest": "XMLHttpRequest",
        "WebSocket": "WebSocket",
        ".innerHTML": "innerHTML injection",
        "document.write": "document.write",
        "eval(": "eval",
        "new Function": "dynamic Function",
    }
    for token, label in prohibited.items():
        require(token not in content, f"Prototype JavaScript must not use {label}")
    require("localStorage" in content, "Contrast preference should persist locally")
    require("textContent" in content, "Dynamic messages must use textContent")


def main() -> int:
    try:
        index = PROTOTYPE / "index.html"
        css = PROTOTYPE / "styles.css"
        javascript = PROTOTYPE / "app.js"
        for path in (index, css, javascript):
            require(path.is_file(), f"Missing prototype file: {path}")

        validate_html(index)
        validate_css(css)
        validate_javascript(javascript)
    except PrototypeFailure as exc:
        print(f"PROTOTYPE VALIDATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("Validated prototype isolation, core accessibility, and no-network safety constraints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
