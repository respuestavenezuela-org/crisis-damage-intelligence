#!/usr/bin/env python3
"""Build a metadata-only manifest for hotosm/venezuela_eq_2026.

The goal is source triage, not bulk ingest. This script calls the Hugging Face
tree API, records file paths/sizes/source families, and writes small ops
manifests that can be reviewed before downloading any data layers.
"""

from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATASET = "hotosm/venezuela_eq_2026"
API_ROOT = f"https://huggingface.co/api/datasets/{DATASET}/tree/main"
RESOLVE_ROOT = f"https://huggingface.co/datasets/{DATASET}/resolve/main"
OUT_CSV = ROOT / "ops" / "data_acquisition_plan" / "hotosm_hf_dataset_manifest.csv"
OUT_JSON = ROOT / "ops" / "data_acquisition_plan" / "hotosm_hf_dataset_summary.json"
USER_AGENT = "respuesta-venezuela-hotosm-manifest/1.0"


def utc_stamp() -> str:
  return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_tree(path: str = "") -> list[dict[str, Any]]:
  suffix = f"/{urllib.parse.quote(path)}" if path else ""
  url = f"{API_ROOT}{suffix}?expand=1"
  req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
  with urllib.request.urlopen(req, timeout=60) as response:
    return json.load(response)


def source_family(path: str) -> str:
  parts = path.split("/")
  if "validated_mapswipe" in parts:
    return "validated_mapswipe"
  for family in ("fair", "microsoft", "osu", "combined", "validated"):
    if family in parts:
      return family
  if "buildings" in parts:
    return "buildings"
  if "viz" in parts:
    return "visualization"
  if path.startswith("multisource_damage/"):
    return "multisource_damage"
  return "metadata"


def area_name(path: str) -> str:
  first = path.split("/", 1)[0]
  known = {"caraballeda", "caracas", "catia_la_mar", "la_guaira", "moron", "naiguata"}
  return first if first in known else ""


def file_format(path: str) -> str:
  suffix = Path(path).suffix.lower().lstrip(".")
  return suffix or "directory"


def walk_tree() -> list[dict[str, Any]]:
  pending = [""]
  rows: list[dict[str, Any]] = []
  seen_dirs: set[str] = set()
  while pending:
    current = pending.pop(0)
    for item in fetch_tree(current):
      item_type = item.get("type", "")
      path = item.get("path", "")
      if item_type == "directory":
        if path not in seen_dirs:
          seen_dirs.add(path)
          pending.append(path)
        continue
      last_commit = item.get("lastCommit") if isinstance(item.get("lastCommit"), dict) else {}
      rows.append({
        "dataset": DATASET,
        "path": path,
        "area": area_name(path),
        "source_family": source_family(path),
        "format": file_format(path),
        "size_bytes": item.get("size", 0),
        "lfs_size_bytes": (item.get("lfs") or {}).get("size", ""),
        "last_commit_id": last_commit.get("id", ""),
        "last_commit_date": last_commit.get("date", ""),
        "download_url": f"{RESOLVE_ROOT}/{urllib.parse.quote(path)}",
      })
  return sorted(rows, key=lambda row: row["path"])


def main() -> int:
  checked_at = utc_stamp()
  rows = walk_tree()
  fieldnames = [
    "checked_at",
    "dataset",
    "path",
    "area",
    "source_family",
    "format",
    "size_bytes",
    "lfs_size_bytes",
    "last_commit_id",
    "last_commit_date",
    "download_url",
  ]
  OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
  with OUT_CSV.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
      writer.writerow({"checked_at": checked_at, **row})

  area_counts = Counter(row["area"] or "global" for row in rows)
  family_counts = Counter(row["source_family"] for row in rows)
  summary = {
    "checked_at": checked_at,
    "dataset": DATASET,
    "file_count": len(rows),
    "total_bytes": sum(int(row["size_bytes"] or 0) for row in rows),
    "area_counts": dict(sorted(area_counts.items())),
    "source_family_counts": dict(sorted(family_counts.items())),
    "manifest": str(OUT_CSV.relative_to(ROOT)),
    "note": "Metadata-only manifest. Files are external triage/adjudication sources, not official EMS metrics.",
  }
  OUT_JSON.write_text(json.dumps(summary, indent=2) + "\n")
  print(json.dumps(summary, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
