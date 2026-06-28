#!/usr/bin/env python3
"""Run VLM triage on EMSR884 post-event chips.

This is intentionally labeled as post-event-only triage. It does not replace
official EMS labels and cannot prove absence of damage without before imagery.
"""

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

LOCAL_COGS = {
    "emsr884-aoi02-caracas": OUTPUTS / "emsr884_imagery" / "EMSR884_AOI02_GRA_PRODUCT_PNEO_20260625_1459_ORTHO_cog.tif",
    "emsr884-aoi06-moron": OUTPUTS / "emsr884_imagery" / "EMSR884_AOI06_GRA_PRODUCT_LEGION_20260625_2036_ORTHO_cog.tif",
    "emsr884-aoi08-san-felipe": OUTPUTS / "emsr884_imagery" / "EMSR884_AOI08_GRA_PRODUCT_PNEO_20260625_1500_ORTHO_cog.tif",
    "emsr884-aoi12-caraballeda": OUTPUTS / "emsr884_imagery" / "EMSR884_AOI12_GRA_PRODUCT_LEGION_20260626_1510_ORTHO_cog.tif",
}

SYSTEM = (
    "You are assisting emergency earthquake damage triage from post-event aerial/satellite imagery. "
    "You only see post-event imagery for one EMS mapped built-up feature centered in the chip. "
    "Be conservative: do not treat this as official confirmation and do not infer no damage from a single image. "
    "Return only valid JSON with keys damage_class, damage_percent, confidence, evidence, image_quality, "
    "action_priority, uncertainty_reason. damage_class must be one of no_visible_damage, minor_visible_damage, "
    "possible_major_damage, likely_destroyed, uncertain_imagery_problem. action_priority must be one of "
    "urgent_review, review, deprioritize. Base decisions on visible signs such as roof collapse, rubble, debris field, "
    "distorted footprint, exposed floors, pancaking, shadow/height loss, or severe obstruction/blur."
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


def chip_path(aoi_id: str, feature_id: str) -> Path:
    return ROOT / "public" / "data" / "chips" / aoi_id / f"{feature_id}_post_event.png"


def make_chip(cog: Path, feature: dict, out: Path, size_m: int = 96) -> None:
    props = feature["properties"]
    lat = float(props["centroid_lat"])
    lon = float(props["centroid_lon"])
    x, y = lonlat_to_webmercator(lon, lat)
    half = size_m / 2
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".raw.png")
    cmd = [
        "gdal_translate",
        "--quiet",
        "-of",
        "PNG",
        "-projwin",
        str(x - half),
        str(y + half),
        str(x + half),
        str(y - half),
        "-outsize",
        "512",
        "512",
        str(cog),
        str(tmp),
    ]
    subprocess.run(cmd, check=True)
    from PIL import Image, ImageDraw

    image = Image.open(tmp).convert("RGB")
    draw = ImageDraw.Draw(image)
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


def call_provider(item: dict) -> dict:
    prompt = (
        "Review this post-event satellite/aerial chip for emergency triage. "
        "The white/red reticle marks the EMS mapped feature centroid; inspect the surrounding building footprint. "
        f"AOI: {item['aoi_id']}. Feature: {item['id']}. Official EMS label: {item['ems_damage_gra']}. "
        f"Official EMS percent: {item.get('ems_damage_percent')}. "
        "Because no before image is provided, classify only visible post-event damage indicators and uncertainty. "
        "If the chip is too blurry, dark, obstructed, or does not clearly show the structure, return uncertain_imagery_problem."
    )
    return call_vlm(SYSTEM, prompt, [item["post_event_chip"]], metadata=item, review_type="post_event_only")


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


def make_record(aoi_id: str, cog: Path, feature: dict) -> dict:
    props = feature["properties"]
    fid = props["id"]
    chip = chip_path(aoi_id, fid)
    if not chip.exists():
        make_chip(cog, feature, chip)
    item = {
        "aoi_id": aoi_id,
        "id": fid,
        "ems_damage_gra": props.get("damage_gra"),
        "ems_damage_percent": props.get("damage_percent"),
        "google_maps_url": props.get("google_maps_url"),
        "post_event_chip": str(chip),
    }
    result = call_provider(item)
    public_chip = "/data/chips/" + chip.relative_to(ROOT / "public" / "data" / "chips").as_posix()
    return {
        "id": fid,
        "aoi_id": aoi_id,
        "google_maps_url": props.get("google_maps_url"),
        "official_ems_damage_gra": props.get("damage_gra"),
        "official_ems_damage_percent": props.get("damage_percent"),
        "post_event_chip": public_chip,
        "vlm": result,
    }


def run_aoi(aoi_id: str, limit: int, workers: int) -> int:
    cog = LOCAL_COGS[aoi_id]
    geojson_path = ROOT / "public" / "data" / "aoi" / aoi_id / "damage.geojson"
    out_path = ROOT / "public" / "data" / "aoi" / aoi_id / "vlm_review.jsonl"
    data = json.loads(geojson_path.read_text())
    features = sorted(data.get("features", []), key=priority)
    if limit:
        features = features[:limit]
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                done.add(json.loads(line)["id"])
    pending = [feature for feature in features if feature["properties"]["id"] not in done]

    reviewed = 0
    write_lock = Lock()
    with out_path.open("a") as dst, ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(make_record, aoi_id, cog, feature): feature for feature in pending}
        for future in as_completed(futures):
            feature = futures[future]
            fid = feature["properties"]["id"]
            record = future.result()
            with write_lock:
                if record["id"] in done:
                    continue
                done.add(record["id"])
                reviewed += 1
                dst.write(json.dumps(record, ensure_ascii=True, separators=(",", ":")) + "\n")
                dst.flush()
            result = record["vlm"]
            index = len(done)
            print(f"{aoi_id} {index}/{len(features)} {fid} -> {result.get('damage_class')} conf={result.get('confidence')}", flush=True)
            time.sleep(0.25)
    return reviewed


def main() -> None:
    load_env(ROOT / ".env")
    load_env(ROOT.parents[1] / ".env")
    if len(sys.argv) < 2:
        raise SystemExit("Usage: scripts/run_minimax_ems_post_event_review.py AOI_ID [AOI_ID...] [--limit N]")
    args = sys.argv[1:]
    limit = 0
    workers = int(os.environ.get("VLM_WORKERS", "4"))
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
        if aoi_id not in LOCAL_COGS:
            raise SystemExit(f"No local COG configured for {aoi_id}")
        total += run_aoi(aoi_id, limit, workers)
    print(f"Reviewed {total} new features")


if __name__ == "__main__":
    main()
