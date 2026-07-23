from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen


MANIFEST_NAME = "release-manifest.json"
CHANGESET_PATH = Path("api/deployment-change-set-v183.json")
REPORT_PATH = Path("artifacts/live-publication-v183.json")
EXCLUDED_FROM_MANIFEST = {MANIFEST_NAME, CHANGESET_PATH.as_posix()}
BOOTSTRAP_PATHS = (
    "index.html",
    "sitemap.xml",
    "manifest.webmanifest",
    "sw.js",
    "deployment.json",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Required JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON file: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"JSON root must be an object: {path}")
    return value


def normalized_base_url(base_url: str) -> str:
    value = base_url.strip()
    if not value.startswith(("https://", "http://")):
        raise SystemExit("Base URL must use http or https")
    return value.rstrip("/") + "/"


def file_inventory(site: Path) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for path in sorted(site.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(site).as_posix()
        if relative in EXCLUDED_FROM_MANIFEST:
            continue
        inventory[relative] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    return inventory


def fetch_bytes(url: str, timeout: float = 20.0) -> tuple[int, bytes, dict[str, str]]:
    request = Request(
        url,
        headers={
            "User-Agent": "pterminology-live-publication-v183",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            headers = {key.lower(): value for key, value in response.headers.items()}
            return int(response.status), response.read(), headers
    except HTTPError as exc:
        return int(exc.code), exc.read(), {
            key.lower(): value for key, value in exc.headers.items()
        }
    except URLError as exc:
        raise RuntimeError(f"Network error for {url}: {exc}") from exc


def fetch_json_optional(url: str) -> dict[str, Any] | None:
    try:
        status, body, _ = fetch_bytes(url)
    except RuntimeError:
        return None
    if status != 200:
        return None
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def validate_deployment_stamp(site: Path, expected_sha: str) -> dict[str, Any]:
    deployment = load_json(site / "deployment.json")
    commit = str(deployment.get("commit", "")).strip()
    if commit != expected_sha:
        raise SystemExit(
            json.dumps(
                {"deployment_commit_mismatch": {"expected": expected_sha, "actual": commit}},
                ensure_ascii=False,
            )
        )

    required = {"index.html", "sitemap.xml", "manifest.webmanifest", "sw.js"}
    artifacts = deployment.get("artifacts")
    if not isinstance(artifacts, dict) or not required <= set(artifacts):
        missing = sorted(required - set(artifacts or {}))
        raise SystemExit({"invalid_deployment_artifacts": missing})

    for relative in required:
        path = site / relative
        if not path.is_file():
            raise SystemExit({"missing_deployment_file": relative})
        evidence = artifacts[relative]
        if evidence.get("sha256") != sha256_file(path):
            raise SystemExit({"deployment_hash_mismatch": relative})
        if int(evidence.get("bytes", -1)) != path.stat().st_size:
            raise SystemExit({"deployment_size_mismatch": relative})
    return deployment


def prepare(site: Path, expected_sha: str, base_url: str) -> None:
    if not site.is_dir():
        raise SystemExit(f"Site directory not found: {site}")

    deployment = validate_deployment_stamp(site, expected_sha)
    base = normalized_base_url(base_url)
    previous_url = urljoin(base, MANIFEST_NAME) + f"?before={quote(expected_sha)}"
    previous = fetch_json_optional(previous_url)

    files = file_inventory(site)
    if not files:
        raise SystemExit("Refusing to publish an empty site")

    mode = "delta"
    previous_files: dict[str, Any] = {}
    previous_commit = None
    if (
        isinstance(previous, dict)
        and isinstance(previous.get("files"), dict)
        and isinstance(previous.get("commit"), str)
    ):
        previous_files = previous["files"]
        previous_commit = previous["commit"]
    else:
        mode = "bootstrap"

    if mode == "delta":
        changed_or_added = sorted(
            path
            for path, evidence in files.items()
            if path not in previous_files
            or not isinstance(previous_files[path], dict)
            or previous_files[path].get("sha256") != evidence["sha256"]
            or int(previous_files[path].get("bytes", -1)) != evidence["bytes"]
        )
        deleted = sorted(path for path in previous_files if path not in files)
        verify_paths = changed_or_added
    else:
        changed_or_added = sorted(files)
        deleted = []
        verify_paths = [path for path in BOOTSTRAP_PATHS if path in files]

    manifest = {
        "schema_version": 183,
        "commit": expected_sha,
        "source_workflow_run": deployment.get("workflow_run"),
        "generated_at": utc_now(),
        "file_count": len(files),
        "files": files,
    }
    (site / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    changeset = {
        "schema_version": 183,
        "commit": expected_sha,
        "previous_commit": previous_commit,
        "verification_mode": mode,
        "changed_or_added_count": len(changed_or_added),
        "deleted_count": len(deleted),
        "verify_path_count": len(verify_paths),
        "changed_or_added": changed_or_added,
        "deleted": deleted,
        "verify_paths": verify_paths,
        "prepared_at": utc_now(),
    }
    changeset_path = site / CHANGESET_PATH
    changeset_path.parent.mkdir(parents=True, exist_ok=True)
    changeset_path.write_text(
        json.dumps(changeset, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": "prepared",
                "commit": expected_sha,
                "file_count": len(files),
                "verification_mode": mode,
                "changed_or_added": len(changed_or_added),
                "deleted": len(deleted),
                "verify_paths": len(verify_paths),
            },
            ensure_ascii=False,
        )
    )


def content_url(base: str, relative: str, expected_sha: str, attempt: int) -> str:
    safe_path = "/".join(quote(part) for part in relative.split("/"))
    return urljoin(base, safe_path) + (
        f"?publication={quote(expected_sha)}&attempt={attempt}"
    )


def wait_for_commit(
    base: str, expected_sha: str, attempts: int, delay: float
) -> dict[str, Any]:
    last: dict[str, Any] = {}
    for attempt in range(1, attempts + 1):
        url = content_url(base, "deployment.json", expected_sha, attempt)
        try:
            status, body, _ = fetch_bytes(url)
            if status == 200:
                value = json.loads(body.decode("utf-8"))
                if isinstance(value, dict):
                    last = value
                    if value.get("commit") == expected_sha:
                        return value
        except (RuntimeError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        if attempt < attempts:
            time.sleep(delay)

    raise SystemExit(
        json.dumps(
            {
                "live_commit_not_confirmed": {
                    "expected": expected_sha,
                    "actual": last.get("commit"),
                    "attempts": attempts,
                }
            },
            ensure_ascii=False,
        )
    )


def verify_one_file(
    base: str,
    relative: str,
    expected: dict[str, Any],
    expected_sha: str,
    attempts: int = 6,
    delay: float = 3.0,
) -> dict[str, Any]:
    last_status = None
    last_hash = None
    for attempt in range(1, attempts + 1):
        url = content_url(base, relative, expected_sha, attempt)
        try:
            status, body, headers = fetch_bytes(url)
        except RuntimeError:
            status, body, headers = 0, b"", {}
        last_status = status
        last_hash = sha256_bytes(body) if status == 200 else None
        if (
            status == 200
            and last_hash == expected["sha256"]
            and len(body) == int(expected["bytes"])
        ):
            return {
                "path": relative,
                "status": status,
                "sha256": last_hash,
                "bytes": len(body),
                "content_type": headers.get("content-type"),
            }
        if attempt < attempts:
            time.sleep(delay)

    raise SystemExit(
        json.dumps(
            {
                "live_file_mismatch": {
                    "path": relative,
                    "status": last_status,
                    "expected_sha256": expected["sha256"],
                    "actual_sha256": last_hash,
                    "expected_bytes": expected["bytes"],
                }
            },
            ensure_ascii=False,
        )
    )


def verify_deleted_file(
    base: str,
    relative: str,
    expected_sha: str,
    attempts: int = 6,
    delay: float = 3.0,
) -> dict[str, Any]:
    last_status = None
    for attempt in range(1, attempts + 1):
        url = content_url(base, relative, expected_sha, attempt)
        try:
            status, _, _ = fetch_bytes(url)
        except RuntimeError:
            status = 0
        last_status = status
        if status == 404:
            return {"path": relative, "status": 404}
        if attempt < attempts:
            time.sleep(delay)

    raise SystemExit(
        json.dumps(
            {"deleted_file_still_live": {"path": relative, "status": last_status}},
            ensure_ascii=False,
        )
    )


def verify(
    site: Path,
    expected_sha: str,
    base_url: str,
    attempts: int,
    delay: float,
) -> None:
    if not site.is_dir():
        raise SystemExit(f"Site directory not found: {site}")

    validate_deployment_stamp(site, expected_sha)
    manifest = load_json(site / MANIFEST_NAME)
    changeset = load_json(site / CHANGESET_PATH)
    if manifest.get("commit") != expected_sha or changeset.get("commit") != expected_sha:
        raise SystemExit("Manifest or change-set commit does not match expected SHA")

    base = normalized_base_url(base_url)
    live_deployment = wait_for_commit(base, expected_sha, attempts, delay)

    local_manifest_bytes = (site / MANIFEST_NAME).read_bytes()
    manifest_url = content_url(base, MANIFEST_NAME, expected_sha, 1)
    status, live_manifest_bytes, _ = fetch_bytes(manifest_url)
    if status != 200 or live_manifest_bytes != local_manifest_bytes:
        raise SystemExit(
            json.dumps(
                {
                    "live_manifest_mismatch": {
                        "status": status,
                        "expected_sha256": sha256_bytes(local_manifest_bytes),
                        "actual_sha256": sha256_bytes(live_manifest_bytes),
                    }
                },
                ensure_ascii=False,
            )
        )

    files = manifest.get("files")
    if not isinstance(files, dict):
        raise SystemExit("Manifest files must be an object")

    verified_files = []
    for relative in changeset.get("verify_paths", []):
        if relative not in files:
            raise SystemExit({"verify_path_not_in_manifest": relative})
        verified_files.append(
            verify_one_file(base, relative, files[relative], expected_sha)
        )

    verified_deletions = []
    for relative in changeset.get("deleted", []):
        verified_deletions.append(
            verify_deleted_file(base, relative, expected_sha)
        )

    report = {
        "schema_version": 183,
        "status": "published-and-live-confirmed",
        "commit": expected_sha,
        "base_url": base,
        "verified_at": utc_now(),
        "deployment_workflow_run": live_deployment.get("workflow_run"),
        "manifest_file_count": manifest.get("file_count"),
        "verification_mode": changeset.get("verification_mode"),
        "changed_or_added_count": changeset.get("changed_or_added_count"),
        "deleted_count": changeset.get("deleted_count"),
        "verified_file_count": len(verified_files),
        "verified_deletion_count": len(verified_deletions),
        "verified_files": verified_files,
        "verified_deletions": verified_deletions,
    }
    report_path = site.parent / REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and confirm every validated GitHub Pages publication."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("site", type=Path)
    prepare_parser.add_argument("--expected-sha", required=True)
    prepare_parser.add_argument("--base-url", required=True)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("site", type=Path)
    verify_parser.add_argument("--expected-sha", required=True)
    verify_parser.add_argument("--base-url", required=True)
    verify_parser.add_argument("--attempts", type=int, default=36)
    verify_parser.add_argument("--delay", type=float, default=10.0)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected_sha = args.expected_sha.strip().lower()
    if len(expected_sha) != 40 or any(
        char not in "0123456789abcdef" for char in expected_sha
    ):
        raise SystemExit(
            "Expected SHA must be a full 40-character hexadecimal commit"
        )

    if args.command == "prepare":
        prepare(args.site, expected_sha, args.base_url)
    elif args.command == "verify":
        verify(
            args.site,
            expected_sha,
            args.base_url,
            args.attempts,
            args.delay,
        )


if __name__ == "__main__":
    main()
