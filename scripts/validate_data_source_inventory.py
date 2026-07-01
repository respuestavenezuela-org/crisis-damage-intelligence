#!/usr/bin/env python3
"""Validate source inventory URLs without bulk-downloading datasets."""

from __future__ import annotations

import csv
import json
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "ops" / "data_acquisition_plan" / "source_inventory.csv"
OUT = ROOT / "ops" / "data_acquisition_plan" / "source_access_manifest.csv"
SUMMARY = ROOT / "ops" / "data_acquisition_plan" / "source_access_summary.json"
USER_AGENT = "respuesta-venezuela-source-access/1.0"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def response_metadata(resp: Any) -> dict[str, Any]:
    return {
        "content_type": resp.headers.get("Content-Type", ""),
        "content_length": resp.headers.get("Content-Length", ""),
        "accept_ranges": resp.headers.get("Accept-Ranges", ""),
        "final_url": resp.geturl(),
    }


def request_status(url: str, method: str, headers: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "",
        "content_type": "",
        "content_length": "",
        "accept_ranges": "",
        "final_url": "",
        "error": "",
    }
    try:
        req = urllib.request.Request(url, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result["status"] = resp.status
            result.update(response_metadata(resp))
    except HTTPError as exc:
        result["status"] = exc.code
        result["error"] = str(exc)
        result.update(response_metadata(exc))
    except (URLError, TimeoutError) as exc:
        result["error"] = str(exc)
    return result


def validate_url(url: str) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT}
    head = request_status(url, "HEAD", headers)
    ranged = request_status(url, "GET", {**headers, "Range": "bytes=0-0"})
    return {
        "head_status": head["status"],
        "range_status": ranged["status"],
        "range_ok": ranged["status"] in (200, 206),
        "content_type": head["content_type"] or ranged["content_type"],
        "content_length": head["content_length"] or ranged["content_length"],
        "accept_ranges": head["accept_ranges"] or ranged["accept_ranges"],
        "final_url": head["final_url"] or ranged["final_url"],
        "head_error": head["error"],
        "range_error": ranged["error"],
    }


def main() -> int:
    checked_at = utc_stamp()
    with INVENTORY.open(newline="") as handle:
        sources = list(csv.DictReader(handle))

    rows: list[dict[str, Any]] = []
    for source in sources:
        url = source.get("url", "")
        validation = validate_url(url) if url else {}
        rows.append(
            {
                "checked_at": checked_at,
                "priority": source.get("priority", ""),
                "data_type": source.get("data_type", ""),
                "source_name": source.get("source_name", ""),
                "official_status": source.get("official_status", ""),
                "should_use_for_vlm": source.get("should_use_for_vlm", ""),
                "url": url,
                **validation,
            }
        )

    fieldnames = [
        "checked_at",
        "priority",
        "data_type",
        "source_name",
        "official_status",
        "should_use_for_vlm",
        "url",
        "head_status",
        "range_status",
        "range_ok",
        "content_type",
        "content_length",
        "accept_ranges",
        "final_url",
        "head_error",
        "range_error",
    ]
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "checked_at": checked_at,
        "source_count": len(rows),
        "head_200": sum(1 for row in rows if str(row.get("head_status")) == "200"),
        "head_403": sum(1 for row in rows if str(row.get("head_status")) == "403"),
        "range_ok": sum(1 for row in rows if row.get("range_ok") is True),
        "p0_count": sum(1 for row in rows if row.get("priority") == "P0"),
        "p1_count": sum(1 for row in rows if row.get("priority") == "P1"),
        "p2_count": sum(1 for row in rows if row.get("priority") == "P2"),
        "manifest": str(OUT.relative_to(ROOT)),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
