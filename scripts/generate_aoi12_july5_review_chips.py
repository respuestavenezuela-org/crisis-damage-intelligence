#!/usr/bin/env python3
"""Generate same-location AOI12 June 26 / July 5 review chips.

All 26 response-keyword candidates from the June 26 review are extracted from
the official July 5 GeoEye-1 COG. Contact sheets remain operational QA
artifacts. Only the five already-published sites receive public native and
side-by-side evidence images; publication findings still require human review.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_minimax_ems_before_after_review import make_chip  # noqa: E402


EVIDENCE_PATH = ROOT / "public" / "data" / "reconstruction" / "aerial-response-evidence-la-guaira.json"
DAMAGE_PATH = ROOT / "public" / "data" / "aoi" / "emsr884-aoi12-caraballeda" / "damage.geojson"
JUNE_CHIP_DIR = ROOT / "public" / "data" / "chips" / "emsr884-aoi12-caraballeda"
OPS_DIR = ROOT / "ops" / "data_acquisition_plan" / "aoi12_july5_review"
JULY_COG_URL = (
    "https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/"
    "EMSR884/AOI12/GRA_MONIT02/"
    "EMSR884_AOI12_GRA_MONIT02_GEOEYE1_20260705_1505_ORTHO_cog.tif"
)
JULY_COG = f"/vsicurl/{JULY_COG_URL}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_pair(june: Path, july: Path, out: Path) -> None:
    june_image = Image.open(june).convert("RGB")
    july_image = Image.open(july).convert("RGB")
    panel = Image.new("RGB", (1024, 548), (245, 242, 235))
    panel.paste(june_image, (0, 36))
    panel.paste(july_image, (512, 36))
    draw = ImageDraw.Draw(panel)
    draw.rectangle((0, 0, 1024, 35), fill=(20, 21, 18))
    draw.text((14, 10), "JUNE 26 - LEGION - +41 HOURS", fill=(255, 255, 255))
    draw.text((526, 10), "JULY 5 - GEOEYE-1 - +257 HOURS", fill=(255, 255, 255))
    draw.line((512, 0, 512, 548), fill=(245, 242, 235), width=3)
    out.parent.mkdir(parents=True, exist_ok=True)
    panel.save(out, optimize=True)


def make_contact_sheet(paths: list[Path], out: Path, page: int) -> None:
    columns = 4
    rows = 4
    tile_size = 256
    label_height = 30
    sheet = Image.new(
        "RGB",
        (columns * tile_size, rows * (tile_size + label_height)),
        (238, 235, 227),
    )
    draw = ImageDraw.Draw(sheet)
    for index, path in enumerate(paths):
        x = (index % columns) * tile_size
        y = (index // columns) * (tile_size + label_height)
        image = Image.open(path).convert("RGB").resize((tile_size, tile_size))
        sheet.paste(image, (x, y + label_height))
        draw.rectangle((x, y, x + tile_size, y + label_height), fill=(20, 21, 18))
        draw.text((x + 8, y + 8), path.stem.replace("_20260705", ""), fill=(255, 255, 255))
    draw.text((8, sheet.height - 18), f"AOI12 July 5 review sheet {page}", fill=(70, 65, 58))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)


def main() -> None:
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
    evidence = json.loads(EVIDENCE_PATH.read_text())
    damage = json.loads(DAMAGE_PATH.read_text())
    by_id = {
        str(feature.get("properties", {}).get("id")): feature
        for feature in damage.get("features") or []
    }
    candidate_ids = evidence["review"]["candidateIds"]
    published_ids = {observation["chipId"] for observation in evidence["observations"]}
    missing = sorted(set(candidate_ids) - set(by_id))
    if missing:
        raise SystemExit(f"Candidate IDs missing from damage layer: {missing}")

    chip_dir = OPS_DIR / "chips"
    chip_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    failures: list[str] = []
    manifest_rows = []

    for chip_id in candidate_ids:
        out = chip_dir / f"{chip_id}_20260705.png"
        if not out.is_file() and not make_chip(JULY_COG, by_id[chip_id], out):
            failures.append(chip_id)
            continue
        generated.append(out)
        row = {
            "chipId": chip_id,
            "acquisitionUtc": "2026-07-05T15:05:00Z",
            "sensor": "GeoEye-1",
            "sourceUrl": JULY_COG_URL,
            "opsPath": str(out.relative_to(ROOT)),
            "sha256": sha256(out),
            "bytes": out.stat().st_size,
            "published": chip_id in published_ids,
        }
        if chip_id in published_ids:
            pair_ops = OPS_DIR / "comparisons" / f"{chip_id}_20260626_20260705_compare.png"
            june = JUNE_CHIP_DIR / f"{chip_id}_after_event.png"
            if not june.is_file():
                raise SystemExit(f"Missing June 26 native chip: {june}")
            make_pair(june, out, pair_ops)
            row.update(
                {
                    "reviewNativePath": str(out.relative_to(ROOT)),
                    "reviewNativeSha256": sha256(out),
                    "reviewComparePath": str(pair_ops.relative_to(ROOT)),
                    "reviewCompareSha256": sha256(pair_ops),
                }
            )
        manifest_rows.append(row)
        print(f"{chip_id}: {out.stat().st_size} bytes", flush=True)

    for page_index, start in enumerate(range(0, len(generated), 16), start=1):
        make_contact_sheet(
            generated[start : start + 16],
            OPS_DIR / f"contact-sheet-{page_index}.png",
            page_index,
        )

    manifest = {
        "version": 1,
        "aoiId": "emsr884-aoi12-caraballeda",
        "source": {
            "publisher": "Copernicus Emergency Management Service",
            "product": "EMSR884 AOI12 GRA_MONIT02",
            "sensor": "GeoEye-1",
            "acquisitionUtc": "2026-07-05T15:05:00Z",
            "url": JULY_COG_URL,
            "license": "Copernicus EMS public product terms",
        },
        "candidateCount": len(candidate_ids),
        "generatedCount": len(generated),
        "failedIds": failures,
        "publicationRule": (
            "Contact sheets are review aids. A temporal finding may be published only after "
            "human inspection of both dated native chips; absence in one chip is not proof of absence."
        ),
        "chips": manifest_rows,
    }
    (OPS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "candidates": len(candidate_ids),
                "generated": len(generated),
                "failed": len(failures),
                "reviewPairs": len(published_ids),
                "manifest": str((OPS_DIR / "manifest.json").relative_to(ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
