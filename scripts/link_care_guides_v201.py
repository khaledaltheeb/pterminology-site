from __future__ import annotations

import re

import link_care_guides_v21 as legacy


def insert_into_element(text: str, pattern: str, link: str, closing_tag: str, label: str) -> str:
    match = re.search(pattern, text, re.I | re.S)
    if not match:
        raise SystemExit(f"Homepage has no semantic {label} element for care-guide integration")
    element = match.group(0)
    if link in element:
        return text
    updated = re.sub(closing_tag, link + closing_tag.replace("\\", ""), element, count=1, flags=re.I)
    return text[: match.start()] + updated + text[match.end() :]


def semantic_inject_once(text: str, marker: str, link: str, label: str) -> str:
    if label == "navigation":
        header = re.search(r"<header\b[^>]*>.*?</header>", text, re.I | re.S)
        if not header:
            raise SystemExit("Homepage header is missing during care-guide integration")
        nav = re.search(r"<nav\b[^>]*>.*?</nav>", header.group(0), re.I | re.S)
        if not nav:
            raise SystemExit("Homepage navigation is missing during care-guide integration")
        nav_html = nav.group(0)
        if link in nav_html:
            return text
        updated_nav = re.sub(r"</nav>", link + "</nav>", nav_html, count=1, flags=re.I)
        start = header.start() + nav.start()
        end = header.start() + nav.end()
        return text[:start] + updated_nav + text[end:]
    if label == "hero action":
        hero = re.search(r"<section\b[^>]*class=[\"'][^\"']*hero[^\"']*[\"'][^>]*>.*?</section>", text, re.I | re.S)
        if not hero:
            raise SystemExit("Homepage hero is missing during care-guide integration")
        actions = re.search(r"<div\b[^>]*class=[\"'][^\"']*actions[^\"']*[\"'][^>]*>.*?</div>", hero.group(0), re.I | re.S)
        if not actions:
            raise SystemExit("Homepage hero actions are missing during care-guide integration")
        actions_html = actions.group(0)
        if link in actions_html:
            return text
        updated_actions = re.sub(r"</div>", link + "</div>", actions_html, count=1, flags=re.I)
        start = hero.start() + actions.start()
        end = hero.start() + actions.end()
        return text[:start] + updated_actions + text[end:]
    return legacy.inject_once(text, marker, link, label)


def main() -> None:
    legacy.inject_once = semantic_inject_once
    legacy.main()


if __name__ == "__main__":
    main()
