from __future__ import annotations

import base64
import gzip
import json
import tarfile
from pathlib import Path

PARTS = [Path(f".v12bundle/part{i:02d}") for i in range(4)]
OUTPUT = Path("/tmp/v12-source.tar.gz")


def main() -> None:
    missing = [str(path) for path in PARTS if not path.exists()]
    if missing:
        raise SystemExit(f"Missing v12 bundle parts: {missing}")

    encoded = "".join(
        "".join(path.read_text(encoding="utf-8").split()) for path in PARTS
    )
    encoded += "=" * (-len(encoded) % 4)
    data = base64.b64decode(encoded, validate=False)
    gzip.decompress(data)
    OUTPUT.write_bytes(data)

    with tarfile.open(OUTPUT, "r:gz") as archive:
        names = archive.getnames()
        if len(names) < 9:
            raise SystemExit(f"Incomplete v12 archive: {names}")
        archive.extractall(".")

    root = Path("content/v12")
    sources = sorted(root.glob("assessments-*.json")) + [root / "games-v12.json"]
    for path in sources:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("count") != len(payload.get("items", [])):
            raise SystemExit(f"Count mismatch in {path}")

    print(
        json.dumps(
            {
                "encoded_chars": len(encoded),
                "archive_bytes": len(data),
                "archive_files": len(names),
                "json_sources": len(sources),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
