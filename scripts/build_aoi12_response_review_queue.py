#!/usr/bin/env python3
"""Build a human-review queue and contact sheets from AOI12 response VLM triage."""

from __future__ import annotations

import argparse
import csv
import json
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OPS_BASE = ROOT / "ops" / "data_acquisition_plan" / "aoi12_temporal_response_grid"
OUT_BASE = ROOT / "output" / "aoi12_temporal_response_grid"
OPS_DIR = OPS_BASE
RESULTS = OPS_DIR / "hf_primary.jsonl"
QUEUE_CSV = OPS_DIR / "human_review_queue.csv"
QUEUE_JSON = OPS_DIR / "human_review_queue.json"
OUT_DIR = OUT_BASE / "review"
SECONDARY = OPS_DIR / "hf_secondary_adjudication.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="coarse-500m")
    parser.add_argument(
        "--mode",
        choices=("all", "likely-or-agreement", "agreement"),
        default="all",
    )
    return parser.parse_args()


def configure_profile(profile: str, mode: str) -> None:
    global OPS_DIR, RESULTS, SECONDARY, QUEUE_CSV, QUEUE_JSON, OUT_DIR
    if profile == "coarse-500m":
        OPS_DIR = OPS_BASE
        OUT_DIR = OUT_BASE / "review"
    else:
        OPS_DIR = OPS_BASE / profile
        OUT_DIR = OUT_BASE / profile / "review"
    RESULTS = OPS_DIR / "hf_primary.jsonl"
    SECONDARY = OPS_DIR / "hf_secondary_adjudication.jsonl"
    suffix = "" if mode == "all" else f"_{mode.replace('-', '_')}"
    QUEUE_CSV = OPS_DIR / f"human_review_queue{suffix}.csv"
    QUEUE_JSON = OPS_DIR / f"human_review_queue{suffix}.json"
    if mode != "all":
        OUT_DIR = OUT_DIR / mode


def read_results() -> list[dict[str, Any]]:
    return [json.loads(line) for line in RESULTS.read_text().splitlines() if line.strip()]


def is_candidate(record: dict[str, Any], secondary: dict[str, dict[str, Any]], mode: str) -> bool:
    vlm = record["vlm"]
    primary_candidate = (
        vlm.get("response_class") in {"likely_response_signal", "possible_response_signal"}
        or vlm.get("human_review_priority") == "high"
    )
    secondary_positive = (
        record["cellId"] in secondary
        and secondary[record["cellId"]]["vlm"].get("response_class")
        in {"likely_response_signal", "possible_response_signal"}
    )
    if mode == "agreement":
        return secondary_positive and vlm.get("response_class") in {
            "likely_response_signal",
            "possible_response_signal",
        }
    if mode == "likely-or-agreement":
        return vlm.get("response_class") == "likely_response_signal" or secondary_positive
    return primary_candidate


def score(record: dict[str, Any]) -> tuple[int, float, str]:
    vlm = record["vlm"]
    cls = vlm.get("response_class")
    priority = vlm.get("human_review_priority")
    rank = {
        ("likely_response_signal", "high"): 0,
        ("likely_response_signal", "medium"): 1,
        ("possible_response_signal", "high"): 2,
        ("possible_response_signal", "medium"): 3,
        ("uncertain_imagery_or_alignment", "high"): 4,
    }.get((cls, priority), 5)
    try:
        confidence = float(vlm.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0
    return rank, -confidence, record["cellId"]


def flatten(
    record: dict[str, Any],
    rank: int,
    secondary: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    vlm = record["vlm"]
    assets = vlm.get("observed_assets")
    if not isinstance(assets, list):
        assets = []
    secondary_vlm = secondary.get(record["cellId"], {}).get("vlm", {})
    return {
        "rank": rank,
        "cell_id": record["cellId"],
        "center_lat": record["centerLat"],
        "center_lon": record["centerLon"],
        "response_class": vlm.get("response_class"),
        "confidence": vlm.get("confidence"),
        "human_review_priority": vlm.get("human_review_priority"),
        "first_visible_date": vlm.get("first_visible_date"),
        "last_absent_date": vlm.get("last_absent_date"),
        "observed_assets": " | ".join(str(asset) for asset in assets),
        "temporal_change": vlm.get("temporal_change"),
        "evidence": vlm.get("evidence"),
        "image_quality": vlm.get("image_quality"),
        "alignment_quality": vlm.get("alignment_quality"),
        "uncertainty_reason": vlm.get("uncertainty_reason"),
        "secondary_response_class": secondary_vlm.get("response_class"),
        "secondary_confidence": secondary_vlm.get("confidence"),
        "secondary_observed_assets": " | ".join(
            str(asset)
            for asset in (
                secondary_vlm.get("observed_assets")
                if isinstance(secondary_vlm.get("observed_assets"), list)
                else []
            )
        ),
        "scene_ids": " | ".join(scene["sceneId"] for scene in record["scenes"]),
        "human_status": "pending",
        "human_finding": "",
        "human_notes": "",
    }


def text_lines(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, width: int, fill=(230, 230, 224)) -> int:
    chars = max(24, width // 7)
    lines = textwrap.wrap(text, width=chars)[:3]
    for line in lines:
        draw.text((x, y), line, fill=fill)
        y += 15
    return y


def render_row(
    record: dict[str, Any],
    rank: int,
    secondary: dict[str, dict[str, Any]],
) -> Image.Image:
    scenes = record["scenes"]
    thumb_w = 228
    thumb_h = 243
    header_h = 104
    width = max(1180, 18 + len(scenes) * (thumb_w + 8))
    panel = Image.new("RGB", (width, header_h + thumb_h + 16), (18, 19, 17))
    draw = ImageDraw.Draw(panel)
    vlm = record["vlm"]
    secondary_vlm = secondary.get(record["cellId"], {}).get("vlm", {})
    draw.text(
        (14, 10),
        (
            f"#{rank:02d} {record['cellId']} | {vlm.get('response_class')} "
            f"| conf={vlm.get('confidence')} | review={vlm.get('human_review_priority')} "
            f"| secondary={secondary_vlm.get('response_class') or 'not-run'}"
        ),
        fill=(211, 255, 62),
    )
    draw.text(
        (14, 29),
        f"{record['centerLat']}, {record['centerLon']} | first={vlm.get('first_visible_date')} | last-absent={vlm.get('last_absent_date')}",
        fill=(240, 240, 234),
    )
    assets = vlm.get("observed_assets") if isinstance(vlm.get("observed_assets"), list) else []
    y = text_lines(draw, "Assets: " + " | ".join(str(asset) for asset in assets), 14, 49, width - 28)
    text_lines(draw, "Change: " + str(vlm.get("temporal_change") or ""), 14, y, width - 28, fill=(190, 190, 184))

    x = 14
    for scene in scenes:
        source = ROOT / scene["chipPath"]
        image = Image.open(source).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb_w, thumb_h), (5, 5, 5))
        tile.paste(image, ((thumb_w - image.width) // 2, (thumb_h - image.height) // 2))
        panel.paste(tile, (x, header_h))
        draw.rectangle((x, header_h, x + thumb_w - 1, header_h + thumb_h - 1), outline=(95, 95, 88), width=1)
        x += thumb_w + 8
    return panel


def render_contact_sheets(
    records: list[dict[str, Any]],
    secondary: dict[str, dict[str, Any]],
) -> list[str]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, record in enumerate(records, 1):
        row = render_row(record, index, secondary)
        path = OUT_DIR / "candidates" / f"{index:02d}_{record['cellId']}.jpg"
        path.parent.mkdir(parents=True, exist_ok=True)
        row.save(path, quality=91, optimize=True)
        rows.append(row)

    sheets = []
    for page_index in range(0, len(rows), 4):
        page_rows = rows[page_index : page_index + 4]
        width = max(row.width for row in page_rows)
        height = sum(row.height for row in page_rows) + 12 * (len(page_rows) - 1)
        sheet = Image.new("RGB", (width, height), (235, 232, 225))
        y = 0
        for row in page_rows:
            sheet.paste(row, (0, y))
            y += row.height + 12
        path = OUT_DIR / f"contact-sheet-{page_index // 4 + 1:02d}.jpg"
        sheet.save(path, quality=92, optimize=True)
        sheets.append(str(path.relative_to(ROOT)))
    return sheets


def main() -> int:
    args = parse_args()
    configure_profile(args.profile, args.mode)
    secondary = {}
    if SECONDARY.is_file():
        secondary = {
            record["cellId"]: record
            for record in (
                json.loads(line) for line in SECONDARY.read_text().splitlines() if line.strip()
            )
        }
    records = sorted(
        (
            record
            for record in read_results()
            if is_candidate(record, secondary, args.mode)
        ),
        key=score,
    )
    rows = [flatten(record, rank, secondary) for rank, record in enumerate(records, 1)]
    fieldnames = list(rows[0]) if rows else []
    with QUEUE_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    sheets = render_contact_sheets(records, secondary)
    queue = {
        "version": 1,
        "aoiId": "emsr884-aoi12-caraballeda",
        "candidateCount": len(records),
        "mode": args.mode,
        "status": "pending-human-review",
        "selectionRule": (
            "HF primary likely/possible response signals plus any high-priority uncertain cell. "
            "No record is publishable without native-pixel human adjudication."
        ),
        "records": rows,
        "contactSheets": sheets,
    }
    QUEUE_JSON.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"candidates": len(records), "contactSheets": len(sheets)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
