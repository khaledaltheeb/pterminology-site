from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

DATA = Path("content/v18/care-guides-ar.json")
REQUIRED_GUIDE_FIELDS = {
    "slug",
    "title",
    "audience",
    "search_intent",
    "summary",
    "sources",
}
PROHIBITED = (
    "شخّص نفسك",
    "تشخيص مؤكد",
    "يغني عن الطبيب",
    "بديل عن العلاج",
    "نتيجة نهائية",
)
TRUSTED_HOSTS = {
    "www.who.int",
    "www.unicef.org",
    "www.nice.org.uk",
    "www.cuh.nhs.uk",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def words(value: object) -> int:
    return len(re.findall(r"[\w\u0600-\u06ff]+", str(value), flags=re.UNICODE))


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    guides = payload.get("guides")
    if not isinstance(guides, list) or len(guides) < 6:
        fail("Expected at least six practical care guides")

    slugs: set[str] = set()
    titles: set[str] = set()
    source_urls: set[str] = set()

    for index, guide in enumerate(guides, start=1):
        missing = REQUIRED_GUIDE_FIELDS - set(guide)
        if missing:
            fail(f"Guide {index} missing fields: {sorted(missing)}")

        slug = guide["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            fail(f"Invalid slug: {slug}")
        if slug in slugs:
            fail(f"Duplicate slug: {slug}")
        slugs.add(slug)

        title = guide["title"].strip()
        if title in titles:
            fail(f"Duplicate title: {title}")
        titles.add(title)

        if words(guide["summary"]) < 12:
            fail(f"Summary is too shallow: {slug}")
        if len(guide["search_intent"]) < 3:
            fail(f"Insufficient search-intent coverage: {slug}")
        if len(guide["audience"]) < 2:
            fail(f"Audience definition too narrow: {slug}")

        actionable_lists = [
            value
            for key, value in guide.items()
            if key not in REQUIRED_GUIDE_FIELDS and isinstance(value, list)
        ]
        if not actionable_lists or sum(len(items) for items in actionable_lists) < 7:
            fail(f"Guide lacks actionable depth: {slug}")

        joined = json.dumps(guide, ensure_ascii=False)
        for phrase in PROHIBITED:
            if phrase in joined:
                fail(f"Prohibited diagnostic claim in {slug}: {phrase}")

        sources = guide["sources"]
        if not isinstance(sources, list) or len(sources) < 2:
            fail(f"Guide needs at least two institutional sources: {slug}")
        for source in sources:
            for key in ("publisher", "title", "url", "year"):
                if not source.get(key):
                    fail(f"Incomplete source in {slug}: {key}")
            parsed = urlparse(source["url"])
            if parsed.scheme != "https" or parsed.netloc not in TRUSTED_HOSTS:
                fail(f"Untrusted or non-HTTPS source in {slug}: {source['url']}")
            source_urls.add(source["url"])

    emergency_guides = [guide for guide in guides if guide.get("emergency_note")]
    if len(emergency_guides) < 4:
        fail("Emergency escalation language is missing from too many guides")

    if len(source_urls) < 8:
        fail("Source diversity is insufficient")

    print(
        json.dumps(
            {
                "status": "passed",
                "version": payload["version"],
                "guides": len(guides),
                "unique_sources": len(source_urls),
                "emergency_guides": len(emergency_guides),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
