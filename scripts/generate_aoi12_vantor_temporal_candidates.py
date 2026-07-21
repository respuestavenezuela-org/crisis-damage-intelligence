#!/usr/bin/env python3
"""Extract later-dated Vantor chips for the five published AOI12 sites.

The output is an operational human-review queue, not a published finding.
Vantor scenes are external triage evidence under CC-BY-NC-4.0 and must remain
separate from official Copernicus EMS damage labels.
"""

from __future__ import annotations

import json
import os
import hashlib
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_minimax_ems_before_after_review import make_chip  # noqa: E402


DAMAGE_PATH = ROOT / "public" / "data" / "aoi" / "emsr884-aoi12-caraballeda" / "damage.geojson"
JUNE_CHIP_DIR = ROOT / "public" / "data" / "chips" / "emsr884-aoi12-caraballeda"
OUT_DIR = ROOT / "ops" / "data_acquisition_plan" / "aoi12_vantor_temporal_review"
PUBLIC_DIR = (
    ROOT
    / "public"
    / "data"
    / "reconstruction"
    / "evidence"
    / "la-guaira"
    / "temporal"
)
BASE_URL = (
    "https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/"
    "vantor/venezuela-earthquake-jun-2026"
)
SCENES = {
    "B15000110186C610": {
        "acquisitionUtc": "2026-06-27T13:48:10.374681Z",
        "sensor": "LG05",
        "cloudCover": 6,
        "panGsdM": 0.35,
        "chipIds": ["ems_00031", "ems_00056"],
    },
    "B140001100B5C710": {
        "acquisitionUtc": "2026-06-29T14:09:32.624709Z",
        "sensor": "LG04",
        "cloudCover": 39,
        "panGsdM": 0.41,
        "chipIds": ["ems_00108", "ems_00117", "ems_00119"],
    },
    "B140001100B5C810": {
        "acquisitionUtc": "2026-06-29T14:09:55.124782Z",
        "sensor": "LG04",
        "cloudCover": 41,
        "panGsdM": 0.48,
        "chipIds": ["ems_00108", "ems_00117", "ems_00119"],
    },
}
PUBLISH_SELECTIONS = {
    "ems_00031": "B15000110186C610",
    "ems_00056": "B15000110186C610",
    "ems_00108": "B140001100B5C710",
    "ems_00117": "B140001100B5C710",
    "ems_00119": "B140001100B5C710",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pair(june: Path, later: Path, out: Path, label: str) -> None:
    left = Image.open(june).convert("RGB")
    right = Image.open(later).convert("RGB")
    panel = Image.new("RGB", (1024, 548), (245, 242, 235))
    panel.paste(left, (0, 36))
    panel.paste(right, (512, 36))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, 1024, 35), fill=(20, 21, 18))
    draw.text((14, 10), "JUNE 26 - COPERNICUS LEGION", fill=(255, 255, 255))
    draw.text((526, 10), label, fill=(255, 255, 255))
    draw.line((512, 0, 512, 548), fill=(245, 242, 235), width=3)
    out.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out, optimize=True)


def main() -> None:
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    features = json.loads(DAMAGE_PATH.read_text())["features"]
    by_id = {str(feature["properties"]["id"]): feature for feature in features}
    rows = []
    failures = []

    for scene_id, scene in SCENES.items():
        url = f"{BASE_URL}/{scene_id}/{scene_id}.tif"
        cog = f"/vsicurl/{url}"
        for chip_id in scene["chipIds"]:
            native = OUT_DIR / "chips" / f"{chip_id}_{scene_id}.png"
            compare = OUT_DIR / "comparisons" / f"{chip_id}_{scene_id}_compare.png"
            if not native.is_file() and not make_chip(cog, by_id[chip_id], native):
                failures.append({"chipId": chip_id, "sceneId": scene_id})
                continue
            pair(
                JUNE_CHIP_DIR / f"{chip_id}_after_event.png",
                native,
                compare,
                f"{scene['acquisitionUtc'][:10]} - VANTOR {scene['sensor']}",
            )
            rows.append(
                row := {
                    "chipId": chip_id,
                    "sceneId": scene_id,
                    **scene,
                    "url": url,
                    "nativePath": str(native.relative_to(ROOT)),
                    "comparePath": str(compare.relative_to(ROOT)),
                    "status": "pending-human-review",
                }
            )
            if PUBLISH_SELECTIONS.get(chip_id) == scene_id:
                PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
                public_native = PUBLIC_DIR / f"{chip_id}_{scene_id}_native.png"
                public_compare = PUBLIC_DIR / f"{chip_id}_{scene_id}_compare.png"
                shutil.copy2(native, public_native)
                shutil.copy2(compare, public_compare)
                row.update(
                    {
                        "status": "human-reviewed-selected",
                        "publicNativePath": f"/{public_native.relative_to(ROOT / 'public').as_posix()}",
                        "publicNativeSha256": sha256(public_native),
                        "publicComparePath": f"/{public_compare.relative_to(ROOT / 'public').as_posix()}",
                        "publicCompareSha256": sha256(public_compare),
                    }
                )
            print(f"{chip_id} {scene_id}", flush=True)

    manifest = {
        "version": 1,
        "aoiId": "emsr884-aoi12-caraballeda",
        "sourceRole": "Vantor Open Data temporal triage evidence; not official EMS",
        "license": "CC-BY-NC-4.0",
        "publicationRule": (
            "Publish only findings visible in native pixels after checking clouds, coverage, "
            "alignment and acquisition time. Do not interpret non-visibility as absence."
        ),
        "records": rows,
        "failures": failures,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"generated": len(rows), "failures": len(failures)}, indent=2))


if __name__ == "__main__":
    main()
