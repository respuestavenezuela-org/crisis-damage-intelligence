#!/usr/bin/env python3
"""Run VLM triage using before/after chips where a baseline exists.

This runner is intentionally separate from the legacy post-event-only review.
It currently supports AOI12 because it has a dated Vantor pre-event reference
mosaic and EMS post-event imagery. Outputs are labeled as VLM triage aids, not
official damage confirmation.
"""

import csv
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from vlm_provider import call_vlm


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT.parent

LOCAL_AFTER_COGS = {
    "emsr884-aoi02-caracas": OUTPUTS / "emsr884_imagery" / "EMSR884_AOI02_GRA_PRODUCT_PNEO_20260625_1459_ORTHO_cog.tif",
    "emsr884-aoi12-caraballeda": OUTPUTS / "emsr884_imagery" / "EMSR884_AOI12_GRA_PRODUCT_LEGION_20260626_1510_ORTHO_cog.tif",
}

LOCAL_BEFORE_COGS = {
    "emsr884-aoi02-caracas": "/vsicurl/https://vantor-opendata.s3.amazonaws.com/events/Venezuela-Earthquake-Jun-2026/B160001100FD1910.tif",
    "emsr884-aoi12-caraballeda": OUTPUTS / "vantor_before_aoi12" / "aoi12_vantor_before_reference_2025-11_2026-04_cog.tif",
}

BEFORE_SOURCE_LABEL = {
    "emsr884-aoi02-caracas": "Vantor Open Data pre-event reference scene B160001100FD1910, 2026-03-20T14:46:55Z, LG06, 1% cloud cover, not official EMS before imagery",
    "emsr884-aoi12-caraballeda": "Vantor Open Data pre-event reference mosaic, 2025-11-03 / 2026-03-21 / 2026-04-07, not official EMS before imagery",
}

SYSTEM = (
    "You are assisting emergency earthquake damage triage by comparing pre-event and post-event aerial/satellite chips. "
    "You will receive a before chip and an after chip for the same EMS mapped feature. "
    "The red/white reticle marks the EMS centroid. A yellow/black outline, when visible, marks the EMS feature footprint/geometry. "
    "Be conservative: VLM output is a triage aid, not official confirmation. "
    "Return only valid JSON with keys damage_class, damage_percent, confidence, change_evidence, before_observation, "
    "after_observation, image_alignment, image_quality, action_priority, uncertainty_reason. "
    "damage_class must be one of no_change_visible, minor_visible_damage, possible_major_damage, likely_destroyed, "
    "uncertain_comparison_problem. action_priority must be one of urgent_review, review, deprioritize. "
    "Focus on visible before/after change: new rubble, roof loss, collapse, footprint distortion, exposed floors, debris fields, "
    "shadow/height loss, or clear disappearance. If alignment, resolution, cloud, black/missing before tile, or scene mismatch prevents "
    "comparison, return uncertain_comparison_problem."
)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def lonlat_to_webmercator(lon: float, lat: float) -> tuple[float, float]:
    radius = 6378137.0
    x = radius * math.radians(lon)
    y = radius * math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0))
    return x, y


def degree_window(lon: float, lat: float, size_m: int) -> tuple[float, float, float, float]:
    half_lat = (size_m / 2) / 111_320
    half_lon = (size_m / 2) / (111_320 * max(0.1, math.cos(math.radians(lat))))
    return lon - half_lon, lat + half_lat, lon + half_lon, lat - half_lat


def lonlat_to_chip_pixel(lon: float, lat: float, window: tuple[float, float, float, float], chip_size: int = 512) -> tuple[float, float]:
    min_lon, max_lat, max_lon, min_lat = window
    x = (lon - min_lon) / (max_lon - min_lon) * chip_size
    y = (max_lat - lat) / (max_lat - min_lat) * chip_size
    return x, y


def geometry_rings(geometry: dict) -> list[list[tuple[float, float]]]:
    if not geometry:
        return []
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if kind == "Polygon":
        return [[(float(lon), float(lat)) for lon, lat, *_ in ring] for ring in coords]
    if kind == "MultiPolygon":
        return [[(float(lon), float(lat)) for lon, lat, *_ in ring] for poly in coords for ring in poly]
    return []


def draw_feature_outline(draw, feature: dict, window: tuple[float, float, float, float], chip_size: int = 512) -> None:
    for ring in geometry_rings(feature.get("geometry", {})):
        points = [lonlat_to_chip_pixel(lon, lat, window, chip_size) for lon, lat in ring]
        visible = [(x, y) for x, y in points if -64 <= x <= chip_size + 64 and -64 <= y <= chip_size + 64]
        if len(visible) < 2:
            continue
        draw.line(points, fill=(0, 0, 0), width=6, joint="curve")
        draw.line(points, fill=(255, 221, 58), width=3, joint="curve")


def chip_path(aoi_id: str, feature_id: str, kind: str) -> Path:
    return ROOT / "public" / "data" / "chips" / aoi_id / f"{feature_id}_{kind}.png"


def cog_exists(cog: str | Path) -> bool:
    return isinstance(cog, str) and cog.startswith("/vsicurl/") or Path(cog).exists()


def make_chip(cog: str | Path, feature: dict, out: Path, size_m: int = 96) -> bool:
    props = feature["properties"]
    lat = float(props["centroid_lat"])
    lon = float(props["centroid_lon"])
    window = degree_window(lon, lat, size_m)
    min_lon, max_lat, max_lon, min_lat = window
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".raw.png")
    cmd = [
        "gdal_translate",
        "--quiet",
        "-of",
        "PNG",
        "-projwin_srs",
        "EPSG:4326",
        "-projwin",
        str(min_lon),
        str(max_lat),
        str(max_lon),
        str(min_lat),
        "-outsize",
        "512",
        "512",
        os.fspath(cog),
        str(tmp),
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return False
    from PIL import Image, ImageDraw, ImageStat

    image = Image.open(tmp).convert("RGB")
    stat = ImageStat.Stat(image)
    # Very dark chips are usually outside a partial pre-event mosaic.
    if sum(stat.mean) / 3 < 4:
        tmp.unlink(missing_ok=True)
        tmp.with_suffix(tmp.suffix + ".aux.xml").unlink(missing_ok=True)
        return False
    draw = ImageDraw.Draw(image)
    draw_feature_outline(draw, feature, window)
    cx = cy = 256
    draw.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), outline=(255, 255, 255), width=4)
    draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), outline=(220, 38, 38), width=3)
    draw.line((cx - 18, cy, cx - 11, cy), fill=(255, 255, 255), width=3)
    draw.line((cx + 11, cy, cx + 18, cy), fill=(255, 255, 255), width=3)
    draw.line((cx, cy - 18, cx, cy - 11), fill=(255, 255, 255), width=3)
    draw.line((cx, cy + 11, cx, cy + 18), fill=(255, 255, 255), width=3)
    image.save(out, optimize=True)
    tmp.unlink(missing_ok=True)
    tmp.with_suffix(tmp.suffix + ".aux.xml").unlink(missing_ok=True)
    return True


def make_compare_chip(before: Path, after: Path, out: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    before_img = Image.open(before).convert("RGB")
    after_img = Image.open(after).convert("RGB")
    panel = Image.new("RGB", (1024, 548), (245, 242, 235))
    panel.paste(before_img, (0, 36))
    panel.paste(after_img, (512, 36))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, 1024, 35), fill=(20, 21, 18))
    draw.text((14, 10), "BEFORE - Vantor pre-event reference", fill=(255, 255, 255))
    draw.text((526, 10), "AFTER - EMS post-event", fill=(255, 255, 255))
    draw.line((512, 0, 512, 548), fill=(245, 242, 235), width=3)
    out.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out, optimize=True)


def call_provider(item: dict) -> dict:
    prompt = (
        "Compare the before and after chips for emergency earthquake damage triage. "
        "Both chips are centered on the same EMS mapped feature centroid marked by the reticle. "
        "If a yellow/black outline is visible, use it as the mapped EMS feature footprint/geometry and evaluate the outlined area, not only the reticle pixel. "
        f"AOI: {item['aoi_id']}. Feature: {item['id']}. Official EMS label: {item['ems_damage_gra']}. "
        f"Official EMS percent: {item.get('ems_damage_percent')}. "
        f"Before source: {item['before_source_label']}. "
        "Assess visible physical change between before and after. Do not rely only on the official EMS label. "
        "If the before reference is missing, too misaligned, lower quality, or from a different viewing geometry that prevents a fair comparison, "
        "return uncertain_comparison_problem and explain why."
    )
    result = call_vlm(
        SYSTEM,
        prompt,
        [item["compare_chip"]],
        metadata=item,
        review_type="dated_pre_event_comparison",
    )
    result["before_source"] = item["before_source_label"]
    return result


def priority(feature: dict) -> tuple[int, str]:
    props = feature["properties"]
    raw = str(props.get("damage_gra") or "").lower()
    if "destroy" in raw:
        return (0, props["id"])
    if raw == "damaged":
        return (1, props["id"])
    if "possibly" in raw or "possible" in raw:
        return (2, props["id"])
    return (9, props["id"])


def public_chip(path: Path) -> str:
    return "/data/chips/" + path.relative_to(ROOT / "public" / "data" / "chips").as_posix()


def make_record(aoi_id: str, before_cog: str | Path, after_cog: str | Path, feature: dict, force: bool = False) -> dict | None:
    props = feature["properties"]
    fid = props["id"]
    before_chip = chip_path(aoi_id, fid, "before_event")
    after_chip = chip_path(aoi_id, fid, "after_event")
    compare_chip = chip_path(aoi_id, fid, "before_after_compare")
    if force:
        before_chip.unlink(missing_ok=True)
        after_chip.unlink(missing_ok=True)
        compare_chip.unlink(missing_ok=True)
    if not before_chip.exists() and not make_chip(before_cog, feature, before_chip):
        return None
    if not after_chip.exists():
        make_chip(after_cog, feature, after_chip)
    if not compare_chip.exists():
        make_compare_chip(before_chip, after_chip, compare_chip)
    item = {
        "aoi_id": aoi_id,
        "id": fid,
        "ems_damage_gra": props.get("damage_gra"),
        "ems_damage_percent": props.get("damage_percent"),
        "before_source_label": BEFORE_SOURCE_LABEL[aoi_id],
        "compare_chip": str(compare_chip),
    }
    result = call_provider(item)
    return {
        "id": fid,
        "aoi_id": aoi_id,
        "google_maps_url": props.get("google_maps_url"),
        "official_ems_damage_gra": props.get("damage_gra"),
        "official_ems_damage_percent": props.get("damage_percent"),
        "before_event_chip": public_chip(before_chip),
        "post_event_chip": public_chip(after_chip),
        "compare_chip": public_chip(compare_chip),
        "vlm": result,
    }


def write_summary(aoi_id: str, records: list[dict]) -> None:
    out_dir = ROOT / "public" / "data" / "aoi" / aoi_id
    summary_path = out_dir / "vlm_before_after_summary.json"
    csv_path = out_dir / "vlm_before_after_summary.csv"
    records = sorted(records, key=lambda record: record["id"])
    classes: dict[str, int] = {}
    priorities: dict[str, int] = {}
    for record in records:
        v = record.get("vlm", {})
        classes[v.get("damage_class", "unknown")] = classes.get(v.get("damage_class", "unknown"), 0) + 1
        priorities[v.get("action_priority", "unknown")] = priorities.get(v.get("action_priority", "unknown"), 0) + 1
    summary = {
        "aoi_id": aoi_id,
        "review_type": "dated_pre_event_comparison",
        "reviewed": len(records),
        "damage_classes": classes,
        "action_priorities": priorities,
        "before_source": BEFORE_SOURCE_LABEL[aoi_id],
        "warning": "VLM before/after outputs are triage aids only; official EMS labels remain source of record.",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "official_ems_damage_gra", "vlm_damage_class", "confidence", "action_priority", "compare_chip", "google_maps_url"])
        writer.writeheader()
        for record in records:
            v = record.get("vlm", {})
            writer.writerow({
                "id": record["id"],
                "official_ems_damage_gra": record.get("official_ems_damage_gra"),
                "vlm_damage_class": v.get("damage_class"),
                "confidence": v.get("confidence"),
                "action_priority": v.get("action_priority"),
                "compare_chip": record.get("compare_chip"),
                "google_maps_url": record.get("google_maps_url"),
            })


def regenerate_chips(aoi_id: str, features: list[dict]) -> int:
    before_cog = LOCAL_BEFORE_COGS[aoi_id]
    after_cog = LOCAL_AFTER_COGS[aoi_id]
    made = 0
    for feature in features:
        fid = feature["properties"]["id"]
        before_chip = chip_path(aoi_id, fid, "before_event")
        after_chip = chip_path(aoi_id, fid, "after_event")
        compare_chip = chip_path(aoi_id, fid, "before_after_compare")
        before_chip.unlink(missing_ok=True)
        after_chip.unlink(missing_ok=True)
        compare_chip.unlink(missing_ok=True)
        if not make_chip(before_cog, feature, before_chip):
            print(f"{aoi_id} {fid} skipped chips-only: missing/black before reference", flush=True)
            continue
        if not make_chip(after_cog, feature, after_chip):
            print(f"{aoi_id} {fid} skipped chips-only: missing/black after reference", flush=True)
            continue
        make_compare_chip(before_chip, after_chip, compare_chip)
        made += 1
        print(f"{aoi_id} {fid} regenerated before/after chips", flush=True)
    return made


def run_aoi(aoi_id: str, limit: int, workers: int, force: bool, chips_only: bool) -> int:
    before_cog = LOCAL_BEFORE_COGS[aoi_id]
    after_cog = LOCAL_AFTER_COGS[aoi_id]
    if not cog_exists(before_cog):
        raise SystemExit(f"Before COG missing: {before_cog}")
    if not cog_exists(after_cog):
        raise SystemExit(f"After COG missing: {after_cog}")
    geojson_path = ROOT / "public" / "data" / "aoi" / aoi_id / "damage.geojson"
    out_path = ROOT / "public" / "data" / "aoi" / aoi_id / "vlm_before_after_review.jsonl"
    data = json.loads(geojson_path.read_text())
    features = sorted(data.get("features", []), key=priority)
    if limit:
        features = features[:limit]
    if chips_only:
        made = regenerate_chips(aoi_id, features)
        if out_path.exists():
            records = [json.loads(line) for line in out_path.read_text().splitlines() if line.strip()]
            write_summary(aoi_id, records)
        print(f"Regenerated {made} before/after chip triplets")
        return 0
    done = set()
    records: list[dict] = []
    if out_path.exists():
        for line in out_path.read_text().splitlines():
          if line.strip():
              record = json.loads(line)
              done.add(record["id"])
              records.append(record)
    force_ids = {feature["properties"]["id"] for feature in features} if force else set()
    if force_ids:
        records = [record for record in records if record["id"] not in force_ids]
        done = {record["id"] for record in records}
    pending = [feature for feature in features if force or feature["properties"]["id"] not in done]
    reviewed = 0
    skipped = 0
    write_lock = Lock()
    mode = "w" if force_ids else "a"
    with out_path.open(mode) as dst, ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        if force_ids:
            for record in records:
                dst.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
        futures = {pool.submit(make_record, aoi_id, before_cog, after_cog, feature, force): feature for feature in pending}
        for future in as_completed(futures):
            feature = futures[future]
            fid = feature["properties"]["id"]
            record = future.result()
            if record is None:
                skipped += 1
                print(f"{aoi_id} {fid} skipped: missing/black before reference", flush=True)
                continue
            with write_lock:
                if record["id"] in done:
                    continue
                done.add(record["id"])
                records.append(record)
                reviewed += 1
                dst.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
                dst.flush()
            result = record["vlm"]
            print(f"{aoi_id} {len(done)}/{len(features)} {fid} -> {result.get('damage_class')} conf={result.get('confidence')}", flush=True)
            time.sleep(0.25)
    write_summary(aoi_id, records)
    print(f"Reviewed {reviewed} new features; skipped {skipped}; total before/after records {len(records)}")
    return reviewed


def main() -> None:
    load_env(ROOT / ".env")
    load_env(ROOT.parents[1] / ".env")
    if len(sys.argv) < 2:
        raise SystemExit("Usage: scripts/run_minimax_ems_before_after_review.py AOI_ID [AOI_ID...] [--limit N] [--workers N] [--force] [--chips-only]")
    args = sys.argv[1:]
    limit = 0
    force = False
    chips_only = False
    workers = int(os.environ.get("VLM_WORKERS", "3"))
    if "--force" in args:
        force = True
        args = [arg for arg in args if arg != "--force"]
    if "--chips-only" in args:
        chips_only = True
        args = [arg for arg in args if arg != "--chips-only"]
    if "--workers" in args:
        index = args.index("--workers")
        workers = int(args[index + 1])
        args = args[:index] + args[index + 2 :]
    if "--limit" in args:
        index = args.index("--limit")
        limit = int(args[index + 1])
        args = args[:index] + args[index + 2 :]
    total = 0
    for aoi_id in args:
        if aoi_id not in LOCAL_BEFORE_COGS:
            raise SystemExit(f"No before/after VLM configuration for {aoi_id}")
        total += run_aoi(aoi_id, limit, workers, force, chips_only)
    print(f"Reviewed {total} new before/after comparisons")


if __name__ == "__main__":
    main()
