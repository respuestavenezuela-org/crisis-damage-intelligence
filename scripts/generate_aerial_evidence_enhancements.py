#!/usr/bin/env python3
"""Generate clearly labeled Swin2SR viewing derivatives for AOI12 evidence chips.

These derivatives are inspection aids. They never replace the native Copernicus
chip, and observations must remain supportable in the native pixels.

This script intentionally keeps the model dependency outside the public runtime:

    python3 scripts/generate_aerial_evidence_enhancements.py
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, Swin2SRForImageSuperResolution


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "public" / "data" / "chips" / "emsr884-aoi12-caraballeda"
OUTPUT_DIR = ROOT / "public" / "data" / "reconstruction" / "evidence" / "la-guaira"
MODEL_ID = "caidas/swin2SR-classical-sr-x2-64"
MODEL_REVISION = "cee1c923c6a37361c6e5650b65dcf4be821e5d52"
CHIP_IDS = (
    "ems_00031",
    "ems_00056",
    "ems_00108",
    "ems_00117",
    "ems_00119",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    processor = AutoImageProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
    model = Swin2SRForImageSuperResolution.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
    ).to(device).eval()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for chip_id in CHIP_IDS:
        source = SOURCE_DIR / f"{chip_id}_after_event.png"
        image = Image.open(source).convert("RGB")
        inputs = {
            key: value.to(device)
            for key, value in processor(image, return_tensors="pt").items()
        }
        with torch.inference_mode():
            outputs = model(**inputs)

        array = outputs.reconstruction.data.squeeze().float().cpu().clamp_(0, 1).numpy()
        array = np.moveaxis(array, source=0, destination=-1)
        array = (array * 255.0).round().astype(np.uint8)
        enhanced = Image.fromarray(array).crop((0, 0, image.width * 2, image.height * 2))
        destination = OUTPUT_DIR / f"{chip_id}_after_event_swin2sr_x2.webp"
        enhanced.save(destination, "WEBP", quality=86, method=6)
        print(
            f"{chip_id}: {image.width}x{image.height} -> "
            f"{enhanced.width}x{enhanced.height}; "
            f"source_sha256={sha256(source)}; "
            f"derived_sha256={sha256(destination)}; "
            f"bytes={destination.stat().st_size}"
        )


if __name__ == "__main__":
    main()
