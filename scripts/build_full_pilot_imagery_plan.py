#!/usr/bin/env python3
"""Build a no-inference imagery and grid plan for the full three-city pilot.

The existing AOI12 response grid is buffered around official EMS features.
This planner expands the deterministic footprint using official and external
triage geometries for Catia La Mar, La Guaira, and Caraballeda, then intersects
that footprint with the live Vantor Open Data STAC collection and known
Copernicus EMS scenes. It downloads metadata only, never imagery.
"""

from __future__ import annotations

import json
import math
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from pyproj import Transformer
from shapely.geometry import Point, box, mapping, shape
from shapely.ops import transform, unary_union


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = (
    ROOT / "ops" / "data_acquisition_plan" / "aoi12_full_pilot_imagery_plan"
)
VANTOR_COLLECTION = (
    "https://vantor-opendata.s3.amazonaws.com/events/"
    "Venezuela-Earthquake-Jun-2026/collection.json"
)
CELL_SIZE_M = 250
CORRIDOR_BUFFER_M = 1000
EVENT_UTC = "2026-06-24T00:00:00Z"
FIRST_72H_END_UTC = "2026-06-27T23:59:59Z"

SOURCE_AOIS = {
    "emsr884-aoi12-caraballeda": {
        "label": "Caraballeda / La Guaira official EMS corridor",
        "role": "official_ems",
    },
    "external-msft-catia-la-mar-predicted-damage": {
        "label": "Catia La Mar",
        "role": "external_triage",
    },
    "external-msft-caraballeda-east-predicted-damage": {
        "label": "Caraballeda East",
        "role": "external_triage",
    },
    "external-msft-catia-la-mar-east-predicted-damage": {
        "label": "Catia La Mar East",
        "role": "external_triage",
    },
    "external-msft-la-guaira-east-predicted-damage": {
        "label": "La Guaira East",
        "role": "external_triage",
    },
}

COPERNICUS_SCENES = [
    {
        "sceneId": "COPERNICUS_LEGION_20260626",
        "acquisitionUtc": "2026-06-26T15:10:00Z",
        "sensor": "Legion",
        "phase": "post",
        "sourceFamily": "copernicus_ems",
        "license": "Copernicus EMS public product terms",
        "panGsdM": None,
        "cloudCoverPercent": None,
        "bounds": [-67.0852916, 10.5720789, -66.8041548, 10.6268948],
        "assetUrl": (
            "https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/"
            "AOI12/GRA_PRODUCT/"
            "EMSR884_AOI12_GRA_PRODUCT_LEGION_20260626_1510_ORTHO_cog.tif"
        ),
    },
    {
        "sceneId": "COPERNICUS_GEOEYE1_20260705",
        "acquisitionUtc": "2026-07-05T15:05:00Z",
        "sensor": "GeoEye-1",
        "phase": "post",
        "sourceFamily": "copernicus_ems",
        "license": "Copernicus EMS public product terms",
        "panGsdM": None,
        "cloudCoverPercent": None,
        "bounds": [-67.0858916, 10.5600296, -66.5412555, 10.6295592],
        "assetUrl": (
            "https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/"
            "AOI12/GRA_MONIT02/"
            "EMSR884_AOI12_GRA_MONIT02_GEOEYE1_20260705_1505_ORTHO_cog.tif"
        ),
    },
]

TO_3857 = Transformer.from_crs(4326, 3857, always_xy=True)
TO_4326 = Transformer.from_crs(3857, 4326, always_xy=True)


def fetch_json(url: str, attempts: int = 4) -> dict[str, Any]:
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(url, timeout=30) as response:
                return json.load(response)
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(attempt)
    raise RuntimeError(f"Unable to fetch {url}")


def load_source_corridors() -> tuple[dict[str, Any], Any]:
    corridors: dict[str, Any] = {}
    for aoi_id in SOURCE_AOIS:
        path = ROOT / "public" / "data" / "aoi" / aoi_id / "damage.geojson"
        data = json.loads(path.read_text())
        centers = []
        for feature in data.get("features") or []:
            props = feature.get("properties") or {}
            lon = props.get("centroid_lon")
            lat = props.get("centroid_lat")
            if lon is not None and lat is not None:
                x, y = TO_3857.transform(float(lon), float(lat))
                centers.append(Point(x, y))
                continue
            geometry = feature.get("geometry")
            if geometry:
                centers.append(
                    transform(TO_3857.transform, shape(geometry)).centroid
                )
        if not centers:
            raise RuntimeError(f"No usable geometries found for {aoi_id}")
        corridors[aoi_id] = unary_union(
            [center.buffer(CORRIDOR_BUFFER_M) for center in centers]
        )
    return corridors, unary_union(list(corridors.values()))


def vantor_inventory(full_corridor_wgs84: Any) -> list[dict[str, Any]]:
    collection = fetch_json(VANTOR_COLLECTION)
    urls = [
        link["href"]
        for link in collection.get("links") or []
        if link.get("rel") == "item"
    ]
    items = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_json, url): url for url in urls}
        for future in as_completed(futures):
            item = future.result()
            geometry = shape(item["geometry"])
            if not geometry.intersects(full_corridor_wgs84):
                continue
            properties = item.get("properties") or {}
            visual = (item.get("assets") or {}).get("visual") or {}
            items.append(
                {
                    "sceneId": item["id"],
                    "acquisitionUtc": properties.get("datetime"),
                    "sensor": properties.get("vehicle_name"),
                    "phase": properties.get("phase"),
                    "sourceFamily": "vantor_open_data",
                    "license": "CC-BY-NC-4.0",
                    "panGsdM": properties.get("pan_gsd"),
                    "cloudCoverPercent": properties.get("eo:cloud_cover"),
                    "offNadirDegrees": properties.get("view:off_nadir"),
                    "publishedUtc": properties.get("published"),
                    "bounds": list(geometry.bounds),
                    "assetUrl": visual.get("href"),
                    "metadataUrl": next(
                        (
                            link.get("href")
                            for link in item.get("links") or []
                            if link.get("rel") == "self"
                        ),
                        None,
                    ),
                }
            )
    items.sort(key=lambda item: (item.get("acquisitionUtc") or "", item["sceneId"]))
    return items


def cell_covered(scene: dict[str, Any], bounds_wgs84: list[float]) -> bool:
    scene_bounds = box(*scene["bounds"])
    return scene_bounds.covers(box(*bounds_wgs84))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_corridors, full_corridor = load_source_corridors()
    full_corridor_wgs84 = transform(TO_4326.transform, full_corridor)
    scenes = vantor_inventory(full_corridor_wgs84) + COPERNICUS_SCENES
    unique_scenes = {scene["sceneId"]: scene for scene in scenes}
    scenes = sorted(
        unique_scenes.values(),
        key=lambda item: (item.get("acquisitionUtc") or "", item["sceneId"]),
    )

    start_x = math.floor(full_corridor.bounds[0] / CELL_SIZE_M) * CELL_SIZE_M
    start_y = math.floor(full_corridor.bounds[1] / CELL_SIZE_M) * CELL_SIZE_M
    end_x = math.ceil(full_corridor.bounds[2] / CELL_SIZE_M) * CELL_SIZE_M
    end_y = math.ceil(full_corridor.bounds[3] / CELL_SIZE_M) * CELL_SIZE_M
    cells = []
    features = []
    row = 0
    y = start_y
    while y < end_y:
        column = 0
        x = start_x
        while x < end_x:
            geometry = box(x, y, x + CELL_SIZE_M, y + CELL_SIZE_M)
            if not full_corridor.intersects(geometry):
                column += 1
                x += CELL_SIZE_M
                continue
            lon0, lat0 = TO_4326.transform(x, y)
            lon1, lat1 = TO_4326.transform(
                x + CELL_SIZE_M, y + CELL_SIZE_M
            )
            bounds_wgs84 = [
                min(lon0, lon1),
                min(lat0, lat1),
                max(lon0, lon1),
                max(lat0, lat1),
            ]
            center_lon, center_lat = TO_4326.transform(
                x + CELL_SIZE_M / 2, y + CELL_SIZE_M / 2
            )
            covered_by = [
                aoi_id
                for aoi_id, corridor in source_corridors.items()
                if corridor.intersects(geometry)
            ]
            covered_scenes = [
                scene["sceneId"]
                for scene in scenes
                if cell_covered(scene, bounds_wgs84)
            ]
            scene_records = [
                unique_scenes[scene_id] for scene_id in covered_scenes
            ]
            pre = [
                scene
                for scene in scene_records
                if scene.get("phase") == "pre"
            ]
            post = [
                scene
                for scene in scene_records
                if scene.get("phase") == "post"
            ]
            first_72h = [
                scene
                for scene in post
                if EVENT_UTC <= (scene.get("acquisitionUtc") or "") <= FIRST_72H_END_UTC
            ]
            later = [
                scene
                for scene in post
                if (scene.get("acquisitionUtc") or "") > FIRST_72H_END_UTC
            ]
            eligibility = (
                "pre_first72_later"
                if pre and first_72h and later
                else "pre_and_first72"
                if pre and first_72h
                else "pre_and_post"
                if pre and post
                else "post_event_only"
                if post
                else "pre_event_only"
                if pre
                else "no_known_scene_coverage"
            )
            cell_id = f"pilot_r{row:03d}_c{column:03d}"
            cell = {
                "cellId": cell_id,
                "row": row,
                "column": column,
                "centerLon": round(center_lon, 8),
                "centerLat": round(center_lat, 8),
                "bounds3857": [x, y, x + CELL_SIZE_M, y + CELL_SIZE_M],
                "boundsWgs84": [round(value, 8) for value in bounds_wgs84],
                "coveredByAois": covered_by,
                "coveredSceneIds": covered_scenes,
                "preSceneCount": len(pre),
                "postSceneCount": len(post),
                "first72hSceneCount": len(first_72h),
                "laterSceneCount": len(later),
                "eligibility": eligibility,
            }
            cells.append(cell)
            features.append(
                {
                    "type": "Feature",
                    "id": cell_id,
                    "properties": {
                        key: value
                        for key, value in cell.items()
                        if key not in {"bounds3857", "boundsWgs84"}
                    },
                    "geometry": mapping(
                        transform(TO_4326.transform, geometry)
                    ),
                }
            )
            column += 1
            x += CELL_SIZE_M
        row += 1
        y += CELL_SIZE_M

    eligibility_counts = Counter(cell["eligibility"] for cell in cells)
    source_counts = Counter(
        aoi_id for cell in cells for aoi_id in cell["coveredByAois"]
    )
    post_scenes = [scene for scene in scenes if scene.get("phase") == "post"]
    known_stack_ids = {
        "B15000110186C610",
        "B140001100B5C710",
        "B140001100B5C810",
        "COPERNICUS_LEGION_20260626",
        "COPERNICUS_GEOEYE1_20260705",
    }
    newly_identified_post = [
        scene for scene in post_scenes if scene["sceneId"] not in known_stack_ids
    ]
    summary = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "La Guaira–Caraballeda–Catia La Mar full pilot",
        "cellSizeM": CELL_SIZE_M,
        "corridorBufferM": CORRIDOR_BUFFER_M,
        "gridCells": len(cells),
        "sourceAoiCellCounts": dict(sorted(source_counts.items())),
        "eligibilityCounts": dict(sorted(eligibility_counts.items())),
        "sceneCount": len(scenes),
        "preEventSceneCount": sum(
            scene.get("phase") == "pre" for scene in scenes
        ),
        "postEventSceneCount": len(post_scenes),
        "newlyIdentifiedPostSceneCount": len(newly_identified_post),
        "newlyIdentifiedPostSceneIds": [
            scene["sceneId"] for scene in newly_identified_post
        ],
        "guardrails": [
            "External Microsoft predictions define triage coverage only, not official damage.",
            "Scene bounds indicate metadata coverage, not necessarily usable pixels.",
            "No visible model signal is not evidence of absence.",
            "Vantor derivatives remain subject to CC-BY-NC-4.0.",
        ],
        "outputs": {
            "cells": str((OUT_DIR / "cells.jsonl").relative_to(ROOT)),
            "cellsGeoJson": str(
                (OUT_DIR / "cells.geojson").relative_to(ROOT)
            ),
            "scenes": str((OUT_DIR / "scenes.json").relative_to(ROOT)),
        },
    }
    (OUT_DIR / "cells.jsonl").write_text(
        "".join(json.dumps(cell) + "\n" for cell in cells)
    )
    (OUT_DIR / "cells.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    (OUT_DIR / "scenes.json").write_text(
        json.dumps({"scenes": scenes}, indent=2) + "\n"
    )
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
