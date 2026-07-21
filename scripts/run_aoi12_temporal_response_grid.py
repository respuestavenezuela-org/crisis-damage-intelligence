#!/usr/bin/env python3
"""Run wall-to-wall temporal response triage across the AOI12 coastal corridor.

This pipeline intentionally differs from the building-centred damage VLM:

* a fixed 500 m grid covers the operational corridor around all official EMS
  features, including roads, yards, schools, ports, and open spaces;
* every usable dated source at a grid cell is supplied to the VLM in temporal
  order;
* the prompt looks for response assets and site use, not structural damage;
* outputs are triage evidence only and require human review against native
  pixels before publication.

Generated chips stay under ``output/`` and are not deployed. Compact manifests
and model outputs are written under ``ops/data_acquisition_plan``.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageStat
from pyproj import Transformer
from shapely.geometry import Point, box
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from vlm_provider import call_vlm  # noqa: E402


AOI_ID = "emsr884-aoi12-caraballeda"
DAMAGE_PATH = ROOT / "public" / "data" / "aoi" / AOI_ID / "damage.geojson"
WORK_BASE = ROOT / "output" / "aoi12_temporal_response_grid"
OPS_BASE = ROOT / "ops" / "data_acquisition_plan" / "aoi12_temporal_response_grid"
WORK_DIR = WORK_BASE
OPS_DIR = OPS_BASE
MANIFEST_PATH = OPS_DIR / "manifest.json"
PRIMARY_PATH = OPS_DIR / "hf_primary.jsonl"
MINIMAX_PATH = OPS_DIR / "minimax_adjudication.jsonl"
HF_SECONDARY_PATH = OPS_DIR / "hf_secondary_adjudication.jsonl"
SUMMARY_PATH = OPS_DIR / "summary.json"

TO_WGS84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
TO_WEB_MERCATOR = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)


@dataclass(frozen=True)
class Scene:
    scene_id: str
    acquisition_utc: str
    sensor: str
    source_role: str
    source: str
    license: str
    coverage: tuple[float, float, float, float]
    preferred_rank: int


SCENES = (
    Scene(
        "VANTOR_PRE_EVENT_MOSAIC",
        "2025-11-03/2026-03-21/2026-04-07",
        "Vantor LG02/LG03/LG06 mosaic",
        "pre_event_reference",
        os.fspath(ROOT.parent / "vantor_before_aoi12" / "aoi12_vantor_before_reference_2025-11_2026-04_cog.tif"),
        "CC-BY-NC-4.0",
        (-67.10, 10.55, -66.79, 10.65),
        0,
    ),
    Scene(
        "COPERNICUS_LEGION_20260626",
        "2026-06-26T15:10:00Z",
        "Legion",
        "post_event_official_context",
        "/vsicurl/https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI12/GRA_PRODUCT/EMSR884_AOI12_GRA_PRODUCT_LEGION_20260626_1510_ORTHO_cog.tif",
        "Copernicus EMS public product terms",
        (-67.0852916, 10.5720789, -66.8041548, 10.6268948),
        10,
    ),
    Scene(
        "VANTOR_B15000110186C610_20260627",
        "2026-06-27T13:48:10Z",
        "LG05",
        "post_event_temporal_triage",
        "/vsicurl/https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/vantor/venezuela-earthquake-jun-2026/B15000110186C610/B15000110186C610.tif",
        "CC-BY-NC-4.0",
        (-67.0431081, 10.5240253, -66.9429447, 10.6425567),
        20,
    ),
    Scene(
        "VANTOR_B140001100B5C810_20260629",
        "2026-06-29T14:09:55Z",
        "LG04",
        "post_event_temporal_triage",
        "/vsicurl/https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/vantor/venezuela-earthquake-jun-2026/B140001100B5C810/B140001100B5C810.tif",
        "CC-BY-NC-4.0",
        (-66.9696728, 10.2629525, -66.8039459, 10.7249832),
        30,
    ),
    Scene(
        "VANTOR_B140001100B5C710_20260629",
        "2026-06-29T14:09:32Z",
        "LG04",
        "post_event_temporal_triage",
        "/vsicurl/https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/vantor/venezuela-earthquake-jun-2026/B140001100B5C710/B140001100B5C710.tif",
        "CC-BY-NC-4.0",
        (-66.8528049, 10.2781486, -66.7180504, 10.7308617),
        31,
    ),
    Scene(
        "COPERNICUS_GEOEYE1_20260705",
        "2026-07-05T15:05:00Z",
        "GeoEye-1",
        "post_event_official_context",
        "/vsicurl/https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI12/GRA_MONIT02/EMSR884_AOI12_GRA_MONIT02_GEOEYE1_20260705_1505_ORTHO_cog.tif",
        "Copernicus EMS public product terms",
        (-67.0858916, 10.5600296, -66.5412555, 10.6295592),
        40,
    ),
)

SYSTEM = (
    "You are performing conservative emergency-response triage on a dated sequence of "
    "aerial/satellite images of the exact same fixed geographic grid cell after the June "
    "24, 2026 Venezuela earthquake. The image labels and dates are authoritative: copy "
    "them exactly and never invent, alter, or infer a date. Look only for visible response "
    "assets or site-use changes: excavators/loaders/cranes, dump/water/fuel/cargo trucks, "
    "ambulance/fire/military-sized vehicles, road clearance, organized material staging, "
    "temporary tents or structures, and large organized gatherings compatible with a "
    "shelter or collection point. Ordinary parked vehicles, permanent industrial equipment, "
    "shipping containers, roof colors, shadows, rubble, and compression artifacts are not "
    "response evidence by themselves. A pre-event image can show that an object or use was "
    "already present. Different sensors, clouds, view angles, and resolution can make a fair "
    "comparison impossible. Never treat non-visibility as proof of absence. Return only JSON "
    "with keys response_class, confidence, image_quality, alignment_quality, observed_assets, "
    "temporal_change, first_visible_date, last_absent_date, evidence, human_review_priority, "
    "uncertainty_reason. response_class must be one of likely_response_signal, "
    "possible_response_signal, no_response_signal_visible, uncertain_imagery_or_alignment. "
    "observed_assets must be an array of short literal observations. confidence must be a "
    "number from 0 to 1. human_review_priority must be high, medium, or low. first_visible_date "
    "and last_absent_date must be an exact supplied date or null."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cell-size-m", type=int, default=500)
    parser.add_argument("--corridor-buffer-m", type=int, default=1000)
    parser.add_argument("--chip-size-px", type=int, default=512)
    parser.add_argument(
        "--profile",
        default="coarse-500m",
        help="Output profile. coarse-500m keeps the legacy root; other names use a subdirectory.",
    )
    parser.add_argument("--generate-workers", type=int, default=6)
    parser.add_argument("--vlm-workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0, help="Limit VLM calls after deterministic grid generation.")
    parser.add_argument("--generate-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    parser.add_argument("--force-chips", action="store_true")
    parser.add_argument("--force-vlm", action="store_true")
    parser.add_argument(
        "--adjudicate-hf-model",
        default="",
        help="Optional independent Hugging Face router model for primary positive/high-priority cells.",
    )
    parser.add_argument("--adjudicate-hf-workers", type=int, default=6)
    parser.add_argument("--adjudicate-minimax", action="store_true")
    return parser.parse_args()


def configure_profile(profile: str) -> None:
    global WORK_DIR, OPS_DIR, MANIFEST_PATH, PRIMARY_PATH, MINIMAX_PATH, HF_SECONDARY_PATH, SUMMARY_PATH
    if profile == "coarse-500m":
        WORK_DIR = WORK_BASE
        OPS_DIR = OPS_BASE
    else:
        WORK_DIR = WORK_BASE / profile
        OPS_DIR = OPS_BASE / profile
    MANIFEST_PATH = OPS_DIR / "manifest.json"
    PRIMARY_PATH = OPS_DIR / "hf_primary.jsonl"
    MINIMAX_PATH = OPS_DIR / "minimax_adjudication.jsonl"
    HF_SECONDARY_PATH = OPS_DIR / "hf_secondary_adjudication.jsonl"
    SUMMARY_PATH = OPS_DIR / "summary.json"


def scene_covers(scene: Scene, lon: float, lat: float, half_m: float) -> bool:
    half_lat = half_m / 111_320
    half_lon = half_m / (111_320 * max(0.1, math.cos(math.radians(lat))))
    min_lon, min_lat, max_lon, max_lat = scene.coverage
    return (
        min_lon <= lon - half_lon
        and lon + half_lon <= max_lon
        and min_lat <= lat - half_lat
        and lat + half_lat <= max_lat
    )


def load_corridor(buffer_m: int):
    data = json.loads(DAMAGE_PATH.read_text())
    points = []
    for feature in data["features"]:
        props = feature.get("properties") or {}
        lon = props.get("centroid_lon")
        lat = props.get("centroid_lat")
        if lon is None or lat is None:
            continue
        x, y = TO_WEB_MERCATOR.transform(float(lon), float(lat))
        points.append(Point(x, y))
    if not points:
        raise RuntimeError("No AOI12 EMS feature centroids were found.")
    # Buffers around every official feature cover the operational urban strip
    # without spending VLM calls on the open sea or empty mountain pixels.
    return unary_union([point.buffer(buffer_m) for point in points])


def build_cells(cell_size_m: int, buffer_m: int) -> list[dict[str, Any]]:
    corridor = load_corridor(buffer_m)
    min_x, min_y, max_x, max_y = corridor.bounds
    start_x = math.floor(min_x / cell_size_m) * cell_size_m
    start_y = math.floor(min_y / cell_size_m) * cell_size_m
    cells = []
    row = 0
    y = start_y
    while y < max_y:
        col = 0
        x = start_x
        while x < max_x:
            geom = box(x, y, x + cell_size_m, y + cell_size_m)
            if corridor.intersects(geom):
                cx = x + cell_size_m / 2
                cy = y + cell_size_m / 2
                lon, lat = TO_WGS84.transform(cx, cy)
                cells.append(
                    {
                        "cellId": f"aoi12_r{row:03d}_c{col:03d}",
                        "row": row,
                        "column": col,
                        "centerLon": round(lon, 8),
                        "centerLat": round(lat, 8),
                        "bounds3857": [x, y, x + cell_size_m, y + cell_size_m],
                    }
                )
            col += 1
            x += cell_size_m
        row += 1
        y += cell_size_m
    return cells


def quality(path: Path) -> dict[str, Any]:
    image = Image.open(path).convert("RGB")
    stat = ImageStat.Stat(image)
    mean = sum(stat.mean) / 3
    stddev = sum(stat.stddev) / 3
    small = image.resize((64, 64))
    pixels = list(small.get_flattened_data())
    valid_ratio = sum(1 for pixel in pixels if max(pixel) > 12) / len(pixels)
    return {
        "mean": round(mean, 2),
        "stddev": round(stddev, 2),
        "validPixelRatio": round(valid_ratio, 4),
        "usable": valid_ratio >= 0.15 and mean >= 5 and stddev >= 2,
    }


def label_chip(path: Path, scene: Scene) -> None:
    image = Image.open(path).convert("RGB")
    panel = Image.new("RGB", (image.width, image.height + 34), (18, 19, 17))
    panel.paste(image, (0, 34))
    draw = ImageDraw.Draw(panel)
    label = f"{scene.acquisition_utc} | {scene.sensor} | {scene.scene_id}"
    draw.text((10, 11), label, fill=(255, 255, 255))
    panel.save(path, optimize=True)


def extract_chip(scene: Scene, cell: dict[str, Any], chip_size_px: int, force: bool) -> tuple[Path | None, dict[str, Any]]:
    chip_dir = WORK_DIR / "chips" / cell["cellId"]
    chip_dir.mkdir(parents=True, exist_ok=True)
    out = chip_dir / f"{scene.scene_id}.png"
    if force:
        out.unlink(missing_ok=True)
    if not out.is_file():
        x0, y0, x1, y1 = cell["bounds3857"]
        raw = out.with_name(out.stem + ".raw.png")
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
            str(chip_size_px),
            str(chip_size_px),
            scene.source,
            os.fspath(raw),
        ]
        env = {
            **os.environ,
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
            "GDAL_HTTP_MULTIRANGE": "YES",
        }
        try:
            subprocess.run(command, check=True, env=env, timeout=180)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            raw.unlink(missing_ok=True)
            return None, {"usable": False, "reason": "gdal-extraction-failed"}
        raw.replace(out)
        Path(str(raw) + ".aux.xml").unlink(missing_ok=True)
        label_chip(out, scene)
    result = quality(out)
    if not result["usable"]:
        out.unlink(missing_ok=True)
        return None, result
    return out, result


def generate_cell(cell: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    lon = cell["centerLon"]
    lat = cell["centerLat"]
    records = []
    for scene in SCENES:
        if not scene_covers(scene, lon, lat, args.cell_size_m / 2):
            continue
        path, qa = extract_chip(scene, cell, args.chip_size_px, args.force_chips)
        records.append(
            {
                "sceneId": scene.scene_id,
                "acquisitionUtc": scene.acquisition_utc,
                "sensor": scene.sensor,
                "sourceRole": scene.source_role,
                "license": scene.license,
                "chipPath": str(path.relative_to(ROOT)) if path else None,
                "quality": qa,
            }
        )
    usable_ids = {record["sceneId"] for record in records if record["chipPath"]}
    has_june26 = "COPERNICUS_LEGION_20260626" in usable_ids
    has_later = any(
        scene_id.startswith("VANTOR_") and "2026062" in scene_id
        or scene_id == "COPERNICUS_GEOEYE1_20260705"
        for scene_id in usable_ids
    )
    return {
        **cell,
        "status": "ready" if has_june26 and has_later else "insufficient-temporal-coverage",
        "scenes": records,
    }


def write_manifest(cells: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    ready = [cell for cell in cells if cell["status"] == "ready"]
    scene_counts = Counter(
        scene["sceneId"]
        for cell in ready
        for scene in cell["scenes"]
        if scene.get("chipPath")
    )
    manifest = {
        "version": 1,
        "aoiId": AOI_ID,
        "analysisType": "wall-to-wall-temporal-response-vlm-triage",
        "profile": args.profile,
        "cellSizeM": args.cell_size_m,
        "chipSizePx": args.chip_size_px,
        "outputGroundSampleDistanceM": round(args.cell_size_m / args.chip_size_px, 4),
        "corridorBufferM": args.corridor_buffer_m,
        "gridCellsConsidered": len(cells),
        "gridCellsReady": len(ready),
        "sceneUsableCellCounts": dict(sorted(scene_counts.items())),
        "sourcePolicy": (
            "Official EMS imagery provides dated context; Vantor imagery is external triage evidence. "
            "Model outputs are not official facts and require human review against native pixels."
        ),
        "absencePolicy": "No visible signal is not evidence that a response asset or site did not exist.",
        "resolutionPolicy": (
            "The output pixel spacing is an extraction target, not new source detail. "
            "Final object claims must remain visible in the native-resolution source pixels."
        ),
        "scenes": [
            {
                "sceneId": scene.scene_id,
                "acquisitionUtc": scene.acquisition_utc,
                "sensor": scene.sensor,
                "sourceRole": scene.source_role,
                "license": scene.license,
                "coverage": scene.coverage,
            }
            for scene in SCENES
        ],
        "cells": cells,
    }
    OPS_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def generate(args: argparse.Namespace) -> dict[str, Any]:
    cells = build_cells(args.cell_size_m, args.corridor_buffer_m)
    completed = []
    with ThreadPoolExecutor(max_workers=args.generate_workers) as executor:
        futures = {executor.submit(generate_cell, cell, args): cell["cellId"] for cell in cells}
        for index, future in enumerate(as_completed(futures), 1):
            completed.append(future.result())
            if index % 25 == 0 or index == len(cells):
                print(f"generated {index}/{len(cells)}", flush=True)
    completed.sort(key=lambda cell: (cell["row"], cell["column"]))
    return write_manifest(completed, args)


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.is_file():
        raise SystemExit(f"Missing {MANIFEST_PATH}; run without --analyze-only first.")
    return json.loads(MANIFEST_PATH.read_text())


def load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    records = {}
    for line in path.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            records[record["cellId"]] = record
    return records


def prompt_for(cell: dict[str, Any], scene_records: list[dict[str, Any]]) -> str:
    supplied = [
        {
            "imageNumber": index + 1,
            "sceneId": scene["sceneId"],
            "date": scene["acquisitionUtc"],
            "sensor": scene["sensor"],
            "role": scene["sourceRole"],
        }
        for index, scene in enumerate(scene_records)
    ]
    x0, y0, x1, y1 = cell.get("bounds3857") or [0, 0, 500, 500]
    cell_width_m = round(abs(float(x1) - float(x0)))
    return (
        f"Grid cell {cell['cellId']} is centered at {cell['centerLat']}, {cell['centerLon']} "
        f"and covers approximately {cell_width_m} by {cell_width_m} metres. Images are supplied in exactly this order: "
        f"{json.dumps(supplied, ensure_ascii=False)}. Inspect the entire cell, not only buildings. "
        "Identify only literal visible response-compatible assets or changes. Compare against the "
        "pre-event reference when supplied so permanent industrial vehicles, containers, and equipment "
        "are not newly attributed to the response. If the same-day June 29 scenes disagree because of "
        "cloud, angle, or coverage, mark the comparison uncertain. A July 5 image may establish persistence "
        "but cannot establish first-72-hour arrival. Set first_visible_date only to the earliest supplied "
        "post-event date where the asset is actually discernible. Set last_absent_date only when an earlier "
        "comparable image clearly covers the same location and the asset is genuinely absent. For a negative "
        "classification, phrase evidence as 'no response signal visible in usable pixels', never as absence."
    )


def normalize_temporal_result(
    result: dict[str, Any],
    scene_records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """Apply deterministic publication guardrails without discarding raw output."""

    normalized = copy.deepcopy(result)
    notes = []
    supplied_dates = {scene["acquisitionUtc"] for scene in scene_records}
    for key in ("first_visible_date", "last_absent_date"):
        value = normalized.get(key)
        if value is not None and value not in supplied_dates:
            notes.append(f"{key} removed because it was not an exact supplied acquisition timestamp")
            normalized[key] = None

    response_class = normalized.get("response_class")
    observed_assets = normalized.get("observed_assets")
    if not isinstance(observed_assets, list):
        notes.append("observed_assets coerced to an empty array because the model returned a non-array value")
        normalized["observed_assets"] = []
        observed_assets = []

    if response_class in {"likely_response_signal", "possible_response_signal"} and not observed_assets:
        notes.append("positive class downgraded because no literal observed asset was supplied")
        normalized["response_class"] = "uncertain_imagery_or_alignment"
        normalized["first_visible_date"] = None

    image_quality = str(normalized.get("image_quality") or "").lower()
    alignment_quality = str(normalized.get("alignment_quality") or "").lower()
    if response_class == "no_response_signal_visible":
        # A negative screen never establishes a last-absent bound unless a
        # later positive observation exists in the same result.
        if normalized.get("last_absent_date") is not None:
            notes.append("last_absent_date removed from a negative-only screen")
            normalized["last_absent_date"] = None
        if any(token in image_quality for token in ("low", "poor", "unusable")) or any(
            token in alignment_quality for token in ("low", "poor", "unusable")
        ):
            notes.append("negative class downgraded because image quality or alignment was inadequate")
            normalized["response_class"] = "uncertain_imagery_or_alignment"
            try:
                normalized["confidence"] = min(float(normalized.get("confidence") or 0), 0.5)
            except (TypeError, ValueError):
                normalized["confidence"] = 0.0

    normalized["guardrailNotes"] = notes
    return normalized, notes


def analyze_cell(cell: dict[str, Any]) -> dict[str, Any]:
    scenes = [
        scene
        for scene in sorted(cell["scenes"], key=lambda item: next(s.preferred_rank for s in SCENES if s.scene_id == item["sceneId"]))
        if scene.get("chipPath")
    ]
    paths = [ROOT / scene["chipPath"] for scene in scenes]
    metadata = {
        "cellId": cell["cellId"],
        "centerLon": cell["centerLon"],
        "centerLat": cell["centerLat"],
        "sceneIds": [scene["sceneId"] for scene in scenes],
        "acquisitionUtc": [scene["acquisitionUtc"] for scene in scenes],
    }
    raw_result = call_vlm(
        SYSTEM,
        prompt_for(cell, scenes),
        paths,
        metadata=metadata,
        review_type="temporal_response_comparison",
    )
    result, guardrail_notes = normalize_temporal_result(raw_result, scenes)
    return {
        "cellId": cell["cellId"],
        "centerLon": cell["centerLon"],
        "centerLat": cell["centerLat"],
        "bounds3857": cell["bounds3857"],
        "scenes": scenes,
        "vlm": result,
        "vlmRaw": raw_result,
        "guardrailNotes": guardrail_notes,
        "warning": (
            "VLM output is triage only. Verify every claim against native pixels; "
            "non-visibility is not proof of absence."
        ),
    }


def write_jsonl(path: Path, records: dict[str, dict[str, Any]]) -> None:
    ordered = sorted(records.values(), key=lambda item: item["cellId"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in ordered))


def summarize(
    manifest: dict[str, Any],
    primary: dict[str, dict[str, Any]],
    secondary: dict[str, dict[str, Any]],
    minimax: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    classes = Counter(str(record["vlm"].get("response_class") or "unknown") for record in primary.values())
    priorities = Counter(str(record["vlm"].get("human_review_priority") or "unknown") for record in primary.values())
    candidate_ids = sorted(
        cell_id
        for cell_id, record in primary.items()
        if record["vlm"].get("response_class") in {"likely_response_signal", "possible_response_signal"}
        or record["vlm"].get("human_review_priority") == "high"
    )
    agreement_ids = sorted(
        cell_id
        for cell_id in candidate_ids
        if cell_id in secondary
        and secondary[cell_id]["vlm"].get("response_class")
        in {"likely_response_signal", "possible_response_signal"}
    )
    secondary_models = Counter(
        str(record["vlm"].get("vlm_model") or "unknown")
        for record in secondary.values()
    )
    summary = {
        "version": 1,
        "aoiId": AOI_ID,
        "gridCellsConsidered": manifest["gridCellsConsidered"],
        "gridCellsReady": manifest["gridCellsReady"],
        "hfPrimaryReviewed": len(primary),
        "hfModel": next((record["vlm"].get("vlm_model") for record in primary.values()), None),
        "responseClassCounts": dict(sorted(classes.items())),
        "humanReviewPriorityCounts": dict(sorted(priorities.items())),
        "humanReviewCandidateCount": len(candidate_ids),
        "humanReviewCandidateIds": candidate_ids,
        "hfSecondaryAdjudicated": len(secondary),
        "hfSecondaryModel": next((record["vlm"].get("vlm_model") for record in secondary.values()), None),
        "hfSecondaryModelCounts": dict(sorted(secondary_models.items())),
        "crossModelPositiveAgreementCount": len(agreement_ids),
        "crossModelPositiveAgreementIds": agreement_ids,
        "minimaxAdjudicated": len(minimax),
        "minimaxStatus": (
            "completed"
            if minimax
            else "not-run-missing-MINIMAX_API_KEY"
            if not os.environ.get("MINIMAX_API_KEY")
            else "not-requested"
        ),
        "publicationStatus": "triage-not-public-facts-pending-human-review",
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "primaryResults": str(PRIMARY_PATH.relative_to(ROOT)),
        "secondaryResults": str(HF_SECONDARY_PATH.relative_to(ROOT)) if secondary else None,
        "minimaxResults": str(MINIMAX_PATH.relative_to(ROOT)) if minimax else None,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


def run_primary(manifest: dict[str, Any], args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    os.environ["VLM_PROVIDER"] = "hf_router"
    os.environ.setdefault("HF_VLM_MODEL", "Qwen/Qwen3-VL-30B-A3B-Instruct")
    existing = {} if args.force_vlm else load_jsonl(PRIMARY_PATH)
    ready = [cell for cell in manifest["cells"] if cell["status"] == "ready" and cell["cellId"] not in existing]
    if args.limit:
        ready = ready[: args.limit]
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.vlm_workers) as executor:
        futures = {executor.submit(analyze_cell, cell): cell["cellId"] for cell in ready}
        for index, future in enumerate(as_completed(futures), 1):
            cell_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                print(f"{cell_id}: ERROR {exc}", file=sys.stderr, flush=True)
                continue
            with lock:
                existing[cell_id] = record
                write_jsonl(PRIMARY_PATH, existing)
            print(f"hf {index}/{len(ready)} {cell_id} {record['vlm'].get('response_class')}", flush=True)
    return existing


def run_minimax_adjudication(
    primary: dict[str, dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, dict[str, Any]]:
    if not args.adjudicate_minimax:
        return load_jsonl(MINIMAX_PATH)
    if not os.environ.get("MINIMAX_API_KEY"):
        print("MINIMAX_API_KEY missing; selective adjudication was not run.", file=sys.stderr)
        return {}
    existing = {} if args.force_vlm else load_jsonl(MINIMAX_PATH)
    candidates = [
        record
        for record in primary.values()
        if record["cellId"] not in existing
        and (
            record["vlm"].get("response_class") in {"likely_response_signal", "possible_response_signal"}
            or record["vlm"].get("human_review_priority") == "high"
        )
    ]
    os.environ["VLM_PROVIDER"] = "minimax"
    for index, primary_record in enumerate(candidates, 1):
        cell = {
            "cellId": primary_record["cellId"],
            "centerLon": primary_record["centerLon"],
            "centerLat": primary_record["centerLat"],
        }
        scenes = primary_record["scenes"]
        paths = [ROOT / scene["chipPath"] for scene in scenes]
        result = call_vlm(
            SYSTEM,
            prompt_for(cell, scenes)
            + " Independently adjudicate the imagery; do not defer to another model's result.",
            paths,
            metadata={"cellId": cell["cellId"], "adjudicationOf": "hf_primary"},
            review_type="temporal_response_comparison",
        )
        existing[cell["cellId"]] = {
            "cellId": cell["cellId"],
            "centerLon": cell["centerLon"],
            "centerLat": cell["centerLat"],
            "vlm": result,
        }
        write_jsonl(MINIMAX_PATH, existing)
        print(f"minimax {index}/{len(candidates)} {cell['cellId']} {result.get('response_class')}", flush=True)
    os.environ["VLM_PROVIDER"] = "hf_router"
    return existing


def run_hf_secondary_adjudication(
    primary: dict[str, dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, dict[str, Any]]:
    if not args.adjudicate_hf_model:
        return load_jsonl(HF_SECONDARY_PATH)
    existing = {} if args.force_vlm else load_jsonl(HF_SECONDARY_PATH)
    candidates = [
        record
        for record in primary.values()
        if record["cellId"] not in existing
        and (
            record["vlm"].get("response_class") in {"likely_response_signal", "possible_response_signal"}
            or record["vlm"].get("human_review_priority") == "high"
        )
    ]
    os.environ["VLM_PROVIDER"] = "hf_router"
    os.environ["HF_VLM_MODEL"] = args.adjudicate_hf_model

    def adjudicate(primary_record: dict[str, Any]) -> dict[str, Any]:
        cell = {
            "cellId": primary_record["cellId"],
            "centerLon": primary_record["centerLon"],
            "centerLat": primary_record["centerLat"],
            "bounds3857": primary_record["bounds3857"],
        }
        scenes = primary_record["scenes"]
        paths = [ROOT / scene["chipPath"] for scene in scenes]
        raw = call_vlm(
            SYSTEM,
            prompt_for(cell, scenes)
            + " This is an independent second-model adjudication. Ignore any assumption that a prior model was positive.",
            paths,
            metadata={"cellId": cell["cellId"], "adjudicationOf": "hf_primary"},
            review_type="temporal_response_comparison",
        )
        normalized, notes = normalize_temporal_result(raw, scenes)
        return {
            "cellId": cell["cellId"],
            "centerLon": cell["centerLon"],
            "centerLat": cell["centerLat"],
            "bounds3857": cell["bounds3857"],
            "scenes": scenes,
            "vlm": normalized,
            "vlmRaw": raw,
            "guardrailNotes": notes,
        }

    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.adjudicate_hf_workers) as executor:
        futures = {executor.submit(adjudicate, record): record["cellId"] for record in candidates}
        for index, future in enumerate(as_completed(futures), 1):
            cell_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                print(f"secondary {cell_id}: ERROR {exc}", file=sys.stderr, flush=True)
                continue
            with lock:
                existing[cell_id] = record
                write_jsonl(HF_SECONDARY_PATH, existing)
            print(
                f"secondary {index}/{len(candidates)} {cell_id} {record['vlm'].get('response_class')}",
                flush=True,
            )

    os.environ["HF_VLM_MODEL"] = "Qwen/Qwen3-VL-30B-A3B-Instruct"
    return existing


def main() -> int:
    args = parse_args()
    configure_profile(args.profile)
    if args.generate_only and args.analyze_only:
        raise SystemExit("--generate-only and --analyze-only are mutually exclusive.")
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OPS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest() if args.analyze_only else generate(args)
    if args.generate_only:
        print(
            json.dumps(
                {
                    "gridCellsConsidered": manifest["gridCellsConsidered"],
                    "gridCellsReady": manifest["gridCellsReady"],
                    "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
                },
                indent=2,
            )
        )
        return 0

    primary = run_primary(manifest, args)
    secondary = run_hf_secondary_adjudication(primary, args)
    minimax = run_minimax_adjudication(primary, args)
    summarize(manifest, primary, secondary, minimax)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
