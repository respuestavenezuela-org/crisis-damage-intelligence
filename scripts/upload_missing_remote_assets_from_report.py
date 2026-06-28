#!/usr/bin/env python3
"""Upload locally available remote-asset validation failures to R2.

This is a narrow repair tool for validation failures where the object exists
under ``public/`` but returns 404 from the public R2 URL. It deliberately reads a
validator report instead of scanning all tiles, so it is useful for fixing known
gaps without starting a 60k-file Wrangler upload.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "ops" / "remote_asset_validation" / "latest.json"
DEFAULT_BUCKET = "crisis-damage-intelligence"


def content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".png":
        return "image/png"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "application/octet-stream"


def cache_control(path: Path) -> str:
    if path.suffix.lower() in {".webp", ".png", ".jpg", ".jpeg"}:
        return "public, max-age=31536000, immutable"
    return "public, max-age=300"


def load_failures(report_path: Path) -> list[dict[str, Any]]:
    report = json.loads(report_path.read_text())
    failures = report.get("remote_assets", {}).get("failures", [])
    if not isinstance(failures, list):
        raise SystemExit(f"invalid report shape: {report_path}")
    return failures


def wrangler_put(bucket: str, data_path: str, local_path: Path, attempts: int, dry_run: bool) -> dict[str, Any]:
    key = data_path.removeprefix("/")
    cmd = [
        "npx",
        "wrangler",
        "r2",
        "object",
        "put",
        f"{bucket}/{key}",
        "--remote",
        "--file",
        str(local_path),
        "--content-type",
        content_type(local_path),
        "--cache-control",
        cache_control(local_path),
    ]
    if dry_run:
        return {"ok": True, "dry_run": True, "key": key, "path": str(local_path), "cmd": cmd}

    last_error = ""
    for attempt in range(1, attempts + 1):
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        if proc.returncode == 0:
            return {
                "ok": True,
                "key": key,
                "path": str(local_path),
                "bytes": local_path.stat().st_size,
                "attempt": attempt,
            }
        last_error = (proc.stderr or proc.stdout)[-2000:]
        time.sleep(min(8, attempt * 2))
    return {"ok": False, "key": key, "path": str(local_path), "error": last_error}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--bucket", default=DEFAULT_BUCKET)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    failures = load_failures(args.report)
    selected: list[tuple[str, Path]] = []
    skipped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for failure in failures:
        data_path = failure.get("data_path")
        if not isinstance(data_path, str) or not data_path.startswith("/data/"):
            skipped.append({"failure": failure, "reason": "missing data_path"})
            continue
        if data_path in seen:
            continue
        seen.add(data_path)
        local_path = ROOT / "public" / data_path.removeprefix("/")
        if not local_path.exists():
            skipped.append({"data_path": data_path, "reason": "local file missing"})
            continue
        selected.append((data_path, local_path))

    results = []
    for index, (data_path, local_path) in enumerate(selected, 1):
        print(f"[{index}/{len(selected)}] {data_path}", flush=True)
        result = wrangler_put(args.bucket, data_path, local_path, args.attempts, args.dry_run)
        results.append(result)
        print("  ok" if result.get("ok") else "  failed", flush=True)

    ok = sum(1 for item in results if item.get("ok"))
    failed = [item for item in results if not item.get("ok")]
    summary = {
        "report": str(args.report),
        "selected": len(selected),
        "uploaded_or_dry_run_ok": ok,
        "failed": len(failed),
        "skipped": skipped,
        "failed_items": failed,
    }
    print(json.dumps(summary, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
