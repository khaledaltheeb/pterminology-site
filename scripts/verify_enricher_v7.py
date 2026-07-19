#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import py_compile
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = [
    (".enricher-v7/part00", 9000, "db4b3fdb69f82e5b0400bcaf61339509afa492915150929a204d577bdf6ba27a"),
    (".enricher-v7/part01a", 3000, "6363b043bc484b38d033bd6c7ba1b236fdb7eeef2f1872732bb6a42b0074231e"),
    (".enricher-v7/part01b", 3000, "f4d3251465ed3bc8777ed3de82c293ec5de4af36cefd39fc53b8a49194319768"),
    (".enricher-v7/part01c", 3000, "d5a116849f7316aced0ec241001b89bd2f71c30b38c0510cd4330ae664d72675"),
    (".enricher-v7/part02", 458, "6e20c095181d9b4895701148ae81dd2b5c549fe67ea94bdc6a901141a55cf871"),
]
EXPECTED_B85_SIZE = 18458
EXPECTED_B85_SHA256 = "40fb937d2118be227cfaeb7a333694d7c222b93dc9de5a03b5b44fc36c49237a"
EXPECTED_SCRIPT_SIZE = 49607
EXPECTED_SCRIPT_SHA256 = "aada2d9c080cb112b75dc46dd8aaf1866703724ad112a375d170612d849f85b7"
OUTPUT = ROOT / "enrich_site_v7.py"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    print(f"VERIFICATION FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    chunks: list[bytes] = []
    for relative_path, expected_size, expected_hash in PARTS:
        path = ROOT / relative_path
        if not path.is_file():
            fail(f"missing part: {relative_path}")
        data = path.read_bytes()
        actual_size = len(data)
        actual_hash = sha256(data)
        if actual_size != expected_size:
            fail(f"{relative_path} size {actual_size}, expected {expected_size}")
        if actual_hash != expected_hash:
            fail(f"{relative_path} sha256 {actual_hash}, expected {expected_hash}")
        chunks.append(data)
        print(f"PASS part: {relative_path} ({actual_size} bytes, {actual_hash})")

    encoded = b"".join(chunks)
    if len(encoded) != EXPECTED_B85_SIZE:
        fail(f"combined B85 size {len(encoded)}, expected {EXPECTED_B85_SIZE}")
    encoded_hash = sha256(encoded)
    if encoded_hash != EXPECTED_B85_SHA256:
        fail(f"combined B85 sha256 {encoded_hash}, expected {EXPECTED_B85_SHA256}")
    print(f"PASS combined B85: {len(encoded)} bytes, {encoded_hash}")

    try:
        compressed = base64.b85decode(encoded)
    except Exception as exc:
        fail(f"Base85 decoding error: {exc}")

    try:
        script = zlib.decompress(compressed)
    except Exception as exc:
        fail(f"zlib decompression error: {exc}")

    if len(script) != EXPECTED_SCRIPT_SIZE:
        fail(f"decoded script size {len(script)}, expected {EXPECTED_SCRIPT_SIZE}")
    script_hash = sha256(script)
    if script_hash != EXPECTED_SCRIPT_SHA256:
        fail(f"decoded script sha256 {script_hash}, expected {EXPECTED_SCRIPT_SHA256}")

    OUTPUT.write_bytes(script)
    try:
        py_compile.compile(str(OUTPUT), doraise=True)
    except py_compile.PyCompileError as exc:
        fail(f"Python compilation error: {exc}")

    print(f"PASS decoded Python: {len(script)} bytes, {script_hash}")
    print(f"VERIFICATION PASSED: {OUTPUT.relative_to(ROOT)} is authentic and compilable.")


if __name__ == "__main__":
    main()
