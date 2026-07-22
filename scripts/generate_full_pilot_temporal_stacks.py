#!/usr/bin/env python3
"""Build resumable temporal stacks for the full three-city 250 m pilot grid.

The 734 completed AOI12 cells are reused by exact EPSG:3857 bounds. Only
uncovered cells are extracted. For each new cell the script keeps one usable
pre-event reference and the best usable post-event scene per acquisition date,
falling back through metadata-ranked alternatives when pixels are unusable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageStat


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "ops" / "data_acquisition_plan" / "aoi12_full_pilot_imagery_plan"
AOI12 = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "aoi12_temporal_response_grid"
    / "detail-250m-enhanced"
)
OUT = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "full_pilot_temporal_grid"
    / "detail-250m"
)
CHIPS = ROOT / "output" / "full_pilot_temporal_grid" / "detail-250m" / "chips"
CHECKPOINT = OUT / "stacks.jsonl"
SUMMARY = OUT / "summary.json"
SENSOR_GSD = {
    "Legion": 0.35,
    "GeoEye-1": 0.41,
    "LG01": 0.46,
    "LG02": 0.46,
    "LG03": 0.46,
    "LG04": 0.48,
    "LG05": 0.35,
    "LG06": 0.49,
    "WV02": 0.94,
    "WV03": 0.38,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def read_by_cell(path: Path) -> dict[str, dict[str, Any]]:
    return {row["cellId"]: row for row in read_rows(path)}


def write_checkpoint(records: dict[str, dict[str, Any]]) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    temporary = CHECKPOINT.with_suffix(".jsonl.tmp")
    temporary.write_text(
        "".join(
            json.dumps(record) + "\n"
            for record in sorted(records.values(), key=lambda row: row["cellId"])
        )
    )
    temporary.replace(CHECKPOINT)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scene_rank(scene: dict[str, Any]) -> tuple[float, float, float, str]:
    cloud = scene.get("cloudCoverPercent")
    cloud = float(cloud) if isinstance(cloud, (int, float)) else 25.0
    gsd = scene.get("panGsdM")
    gsd = (
        float(gsd)
        if isinstance(gsd, (int, float))
        else SENSOR_GSD.get(str(scene.get("sensor")), 0.7)
    )
    off_nadir = scene.get("offNadirDegrees")
    off_nadir = (
        abs(float(off_nadir))
        if isinstance(off_nadir, (int, float))
        else 30.0
    )
    return cloud, gsd, off_nadir, scene["sceneId"]


def pixel_quality(path: Path) -> dict[str, Any]:
    with Image.open(path) as source:
        image = source.convert("RGB")
        stat = ImageStat.Stat(image)
        mean = sum(stat.mean) / 3
        stddev = sum(stat.stddev) / 3
        pixels = list(image.resize((64, 64)).get_flattened_data())
    valid_ratio = sum(1 for pixel in pixels if max(pixel) > 12) / len(pixels)
    return {
        "mean": round(mean, 2),
        "stddev": round(stddev, 2),
        "validPixelRatio": round(valid_ratio, 4),
        "usable": valid_ratio >= 0.15 and mean >= 5 and stddev >= 2,
    }


def label_chip(path: Path, scene: dict[str, Any]) -> None:
    with Image.open(path) as source:
        image = source.convert("RGB")
    panel = Image.new("RGB", (image.width, image.height + 34), (18, 19, 17))
    panel.paste(image, (0, 34))
    draw = ImageDraw.Draw(panel)
    draw.text(
        (10, 11),
        f"{scene['acquisitionUtc']} | {scene['sensor']} | {scene['sceneId']}",
        fill=(255, 255, 255),
    )
    panel.save(path, format="PNG", compress_level=6)


def extract_scene(
    scene: dict[str, Any],
    cell: dict[str, Any],
    *,
    force: bool,
) -> dict[str, Any]:
    directory = CHIPS / cell["cellId"]
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / f"{scene['sceneId']}.png"
    if force:
        out.unlink(missing_ok=True)
    if not out.is_file():
        x0, y0, x1, y1 = cell["bounds3857"]
        raw = out.with_name(out.stem + ".raw.png")
        source = scene["assetUrl"]
        if source.startswith("https://"):
            source = "/vsicurl/" + source
        command = [
            "gdal_translate",
            "--quiet",
            "-of",
            "PNG",
            "-projwin_srs",
            "EPSG:3857",
            "-projwin",
            str(x0),
            str(y1),
            str(x1),
            str(y0),
            "-outsize",
            "768",
            "768",
            source,
            os.fspath(raw),
        ]
        env = {
            **os.environ,
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
            "GDAL_HTTP_MULTIRANGE": "YES",
            "GDAL_HTTP_MAX_RETRY": "5",
            "GDAL_HTTP_RETRY_DELAY": "2",
            "GDAL_HTTP_RETRY_CODES": "429,500,502,503,504",
            "VSI_CACHE": "TRUE",
            "VSI_CACHE_SIZE": "25000000",
        }
        error = None
        for attempt in range(1, 4):
            try:
                subprocess.run(command, check=True, env=env, timeout=240)
                error = None
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                error = f"{type(exc).__name__}: {exc}"
                raw.unlink(missing_ok=True)
                time.sleep(attempt * 2)
        if error:
            return {
                "sceneId": scene["sceneId"],
                "status": "extraction_failed",
                "error": error,
            }
        raw.replace(out)
        Path(str(raw) + ".aux.xml").unlink(missing_ok=True)
        label_chip(out, scene)
    quality = pixel_quality(out)
    if not quality["usable"]:
        out.unlink(missing_ok=True)
        return {
            "sceneId": scene["sceneId"],
            "status": "unusable_pixels",
            "quality": quality,
        }
    return {
        "sceneId": scene["sceneId"],
        "acquisitionUtc": scene["acquisitionUtc"],
        "sensor": scene.get("sensor"),
        "sourceRole": (
            "pre_event_reference"
            if scene.get("phase") == "pre"
            else "post_event_temporal_triage"
        ),
        "phase": scene.get("phase"),
        "sourceFamily": scene.get("sourceFamily"),
        "license": scene.get("license"),
        "panGsdM": scene.get("panGsdM"),
        "cloudCoverPercent": scene.get("cloudCoverPercent"),
        "chipPath": str(out.relative_to(ROOT)),
        "chipSha256": file_sha256(out),
        "quality": quality,
        "status": "usable",
    }


def cell_scene_groups(
    cell: dict[str, Any],
    scenes: dict[str, dict[str, Any]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    covered = [
        scenes[scene_id]
        for scene_id in cell.get("coveredSceneIds") or []
        if scene_id in scenes and scenes[scene_id].get("assetUrl")
    ]
    pre = sorted(
        (scene for scene in covered if scene.get("phase") == "pre"),
        key=scene_rank,
    )
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    if pre:
        groups.append(("pre", pre))
    by_date: dict[str, list[dict[str, Any]]] = {}
    for scene in covered:
        if scene.get("phase") != "post":
            continue
        by_date.setdefault(str(scene["acquisitionUtc"])[:10], []).append(scene)
    for date, candidates in sorted(by_date.items()):
        groups.append((date, sorted(candidates, key=scene_rank)))
    return groups


def process_cell(
    cell: dict[str, Any],
    scenes: dict[str, dict[str, Any]],
    *,
    force: bool,
) -> dict[str, Any]:
    selected = []
    alternatives = []
    for group, candidates in cell_scene_groups(cell, scenes):
        winner = None
        for candidate in candidates:
            result = extract_scene(candidate, cell, force=force)
            if result.get("status") == "usable":
                winner = result
                break
            alternatives.append(
                {
                    **result,
                    "group": group,
                    "acquisitionUtc": candidate.get("acquisitionUtc"),
                    "sensor": candidate.get("sensor"),
                }
            )
        if winner:
            selected.append(winner)
            alternatives.extend(
                {
                    "sceneId": candidate["sceneId"],
                    "group": group,
                    "status": "not_extracted_lower_rank",
                    "acquisitionUtc": candidate.get("acquisitionUtc"),
                    "sensor": candidate.get("sensor"),
                }
                for candidate in candidates
                if candidate["sceneId"] != winner["sceneId"]
            )
    has_pre = any(scene.get("phase") == "pre" for scene in selected)
    has_post = any(scene.get("phase") == "post" for scene in selected)
    return {
        "cellId": cell["cellId"],
        "centerLon": cell["centerLon"],
        "centerLat": cell["centerLat"],
        "bounds3857": cell["bounds3857"],
        "coveredByAois": cell.get("coveredByAois") or [],
        "eligibility": cell.get("eligibility"),
        "stackStatus": (
            "before_after"
            if has_pre and has_post
            else "post_event_only"
            if has_post
            else "pre_event_only"
            if has_pre
            else "no_usable_imagery"
        ),
        "selectedScenes": selected,
        "alternativeScenes": alternatives,
        "selectedSceneCount": len(selected),
        "reusedFromCellId": None,
    }


def main() -> int:
    args = parse_args()
    cells = read_rows(PLAN / "cells.jsonl")
    scenes_payload = json.loads((PLAN / "scenes.json").read_text())
    scenes = {
        scene["sceneId"]: scene
        for scene in scenes_payload.get("scenes") or scenes_payload
    }
    completed = read_rows(AOI12 / "stacks.jsonl")
    completed_by_bounds = {
        tuple(record["bounds3857"]): record for record in completed
    }
    existing = {} if args.force else read_by_cell(CHECKPOINT)
    reused = 0
    for cell in cells:
        if cell["cellId"] in existing:
            continue
        source = completed_by_bounds.get(tuple(cell["bounds3857"]))
        if not source:
            continue
        selected = [
            {
                **scene,
                "status": scene.get("status") or "usable",
                "chipSha256": (
                    scene.get("chipSha256")
                    or file_sha256(ROOT / scene["chipPath"])
                ),
            }
            for scene in source.get("selectedScenes") or []
        ]
        existing[cell["cellId"]] = {
            "cellId": cell["cellId"],
            "centerLon": cell["centerLon"],
            "centerLat": cell["centerLat"],
            "bounds3857": cell["bounds3857"],
            "coveredByAois": cell.get("coveredByAois") or [],
            "eligibility": cell.get("eligibility"),
            "stackStatus": (
                "before_after"
                if any(scene.get("phase") == "pre" for scene in selected)
                else "post_event_only"
            ),
            "selectedScenes": selected,
            "alternativeScenes": source.get("alternativeScenes") or [],
            "selectedSceneCount": len(selected),
            "reusedFromCellId": source["cellId"],
        }
        reused += 1
    write_checkpoint(existing)

    pending = [cell for cell in cells if cell["cellId"] not in existing]
    if args.limit:
        pending = pending[: args.limit]
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_cell, cell, scenes, force=args.force): cell["cellId"]
            for cell in pending
        }
        for index, future in enumerate(as_completed(futures), 1):
            cell_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                print(f"full-pilot {cell_id}: ERROR {exc}", flush=True)
                continue
            with lock:
                existing[cell_id] = record
                write_checkpoint(existing)
            print(
                f"full-pilot {index}/{len(pending)} {cell_id} "
                f"{record['stackStatus']} scenes={record['selectedSceneCount']}",
                flush=True,
            )

    status_counts = Counter(
        record.get("stackStatus") or "unknown" for record in existing.values()
    )
    summary = {
        "version": 1,
        "fullPilotCells": len(cells),
        "completedCells": len(existing),
        "pendingCells": len(cells) - len(existing),
        "reusedCompletedAoi12Cells": sum(
            record.get("reusedFromCellId") is not None for record in existing.values()
        ),
        "newlyExtractedCells": sum(
            record.get("reusedFromCellId") is None for record in existing.values()
        ),
        "stackStatusCounts": dict(sorted(status_counts.items())),
        "selectedSceneImages": sum(
            len(record.get("selectedScenes") or []) for record in existing.values()
        ),
        "selectionPolicy": (
            "Reuse exact completed AOI12 cells; otherwise select one usable pre-event "
            "reference and the best usable scene per post-event acquisition date, "
            "with metadata-ranked fallback."
        ),
        "warnings": [
            "Post-event-only stacks are not before/after evidence.",
            "Image metadata coverage does not guarantee usable pixels.",
            "External Microsoft geometries define triage extent only.",
            "No visible signal is not evidence of absence.",
        ],
        "outputs": {
            "stacks": str(CHECKPOINT.relative_to(ROOT)),
            "chips": str(CHIPS.relative_to(ROOT)),
        },
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
