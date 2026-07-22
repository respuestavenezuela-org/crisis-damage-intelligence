#!/usr/bin/env python3
"""Run conservative VLM extraction on public MapAction response-site maps.

This is a documentary-map workflow, not an object-confirmation workflow. It
extracts labels and bounded visual estimates from dated public products so
they can be compared with the aerial triage package without treating a map
symbol, model estimate, or missing label as a field-verified fact.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_aoi12_temporal_response_grid import load_env  # noqa: E402
from vlm_provider import call_vlm  # noqa: E402


DEFAULT_SOURCE_DIR = ROOT / "tmp" / "pdfs" / "mapaction_sources"
DEFAULT_OUTPUT_DIR = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "mapaction_response_sites"
)

SYSTEM = (
    "You are extracting conservative, structured evidence from dated public "
    "humanitarian maps and aerial/drone map products. Read only labels, legends, "
    "dates, symbols, and clearly visible site layout in the supplied image. Do not "
    "use outside knowledge. A map symbol documents what the source mapped as of its "
    "stated date; it is not proof of when a site opened or of its status before or "
    "after that date. Do not infer absence from a missing label. If asked for a "
    "visual count, return a range and make clear that it is an image estimate, not "
    "an occupancy or capacity figure. Return only valid JSON."
)

CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "mapaction-ma020-infrastructure",
        "kind": "infrastructure_map_series",
        "sourceDate": "2026-07-06",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma020-v2",
        "images": (
            "ma020_pages/page-1.jpg",
            "ma020_pages/page-2.jpg",
            "ma020_pages/page-3.jpg",
        ),
        "prompt": (
            "The three images are the west, centre, and east pages of one La Guaira "
            "infrastructure map series. Extract only legible shelter or camp labels, "
            "reported capacity in people when printed, and named operational "
            "coordination centres. Do not enumerate health or education sites. Return "
            "keys analysis_type, source_date, documented_sites, operational_centres, "
            "extraction_limits. Each site item must contain name, category, page, "
            "reported_capacity_people (integer or null), label_text, and confidence. "
            "Do not invent coordinates or opening dates. Keep the JSON compact."
        ),
    },
    {
        "id": "mapaction-ma018-polideportivo",
        "kind": "camp_layout",
        "sourceDate": "2026-07-07",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma018-v3",
        "images": ("2026-ven-001-ma018-v3.jpg",),
        "prompt": (
            "Extract the dated layout of Campamento Transitorio Polideportivo José "
            "María Vargas. Return keys analysis_type, site_name, source_date, "
            "directly_annotated_services, annotated_sleeping_areas, "
            "visible_small_shelter_units_estimate, visible_large_structures, "
            "vehicle_observations, extraction_limits. The shelter estimate must be "
            "an object with min, max, confidence, and explanation. Count only "
            "clearly separable small tent-like units; do not convert them to people."
        ),
    },
    {
        "id": "mapaction-ma022-playa-grande",
        "kind": "camp_layout",
        "sourceDate": "2026-07-07",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma022-v2",
        "images": ("2026-ven-001-ma022-v2.jpg",),
        "prompt": (
            "Extract the dated layout of Campamento Transitorio Playa Grande. Return "
            "keys analysis_type, site_name, source_date, directly_annotated_services, "
            "annotated_sleeping_areas, visible_small_shelter_units_estimate, "
            "visible_large_structures, vehicle_observations, extraction_limits. The "
            "shelter estimate must be an object with min, max, confidence, and "
            "explanation. Count only clearly separable small tent-like units; do not "
            "convert them to people."
        ),
    },
    {
        "id": "mapaction-ma023-cesar-nieves",
        "kind": "camp_layout",
        "sourceDate": "2026-07-07",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma023-v3",
        "images": ("2026-ven-001-ma023-v3.jpg",),
        "prompt": (
            "Extract the dated layout of Campamento Transitorio Estadio Cesar Nieves. "
            "Return keys analysis_type, site_name, source_date, "
            "directly_annotated_services, annotated_sleeping_areas, "
            "visible_small_shelter_units_estimate, visible_large_structures, "
            "vehicle_observations, extraction_limits. The shelter estimate must be "
            "an object with min, max, confidence, and explanation. Count only "
            "clearly separable small tent-like units; do not convert them to people."
        ),
    },
    {
        "id": "mapaction-ma044-mare-abajo",
        "kind": "camp_layout",
        "sourceDate": "2026-07-11",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma044-v1",
        "images": ("2026-ven-001-ma044-v1.jpg",),
        "prompt": (
            "Extract the dated visible layout of Campamento Transitorio Mare Abajo. "
            "This product is less heavily annotated, so separate literal labels from "
            "visual estimates. Return keys analysis_type, site_name, source_date, "
            "directly_annotated_services, annotated_sleeping_areas, "
            "visible_small_shelter_units_estimate, visible_large_structures, "
            "vehicle_observations, extraction_limits. The shelter estimate must be "
            "an object with min, max, confidence, and explanation. Do not convert "
            "visible units to people."
        ),
    },
    {
        "id": "mapaction-ma032-caraballeda-golf",
        "kind": "service_site_layout",
        "sourceDate": "2026-07-04",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma032-v1",
        "images": ("2026-ven-001-ma032-v1.jpg",),
        "prompt": (
            "Extract only the directly annotated humanitarian services at Campo de "
            "Golf de Caraballeda. Return keys analysis_type, site_name, source_date, "
            "directly_annotated_services, organizations_named, vehicle_observations, "
            "visible_small_shelter_units_estimate, extraction_limits. Use null for "
            "the estimate if this image is not suitable for a defensible count."
        ),
    },
    {
        "id": "mapaction-ma055-ma056-debris",
        "kind": "debris_management_maps",
        "sourceDate": "2026-07-17",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma056-v1",
        "images": (
            "2026-ven-001-ma055-v1.jpg",
            "2026-ven-001-ma056-v1.jpg",
        ),
        "prompt": (
            "The first image maps temporary waste disposal and sorting centres on "
            "16 July; the second maps their proximity to health facilities on "
            "17 July. Extract keys analysis_type, source_dates, named_disposal_sites, "
            "health_facility_distance_records, documented_risk_context, "
            "extraction_limits. Each distance record must copy the printed facility "
            "name and distance_m exactly. Do not infer health impact or operating "
            "status."
        ),
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=("hf_router", "minimax"))
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--max-image-pixels", type=int, default=4096)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def prepare_image(
    source: Path,
    prepared_dir: Path,
    max_pixels: int,
) -> Path:
    prepared_dir.mkdir(parents=True, exist_ok=True)
    target = prepared_dir / f"{source.stem}_max{max_pixels}.jpg"
    if target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
        return target
    with Image.open(source) as image:
        image = image.convert("RGB")
        image.thumbnail((max_pixels, max_pixels), Image.Resampling.LANCZOS)
        image.save(target, "JPEG", quality=92, optimize=True)
    return target


def read_records(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    return {
        row["caseId"]: row
        for row in (
            json.loads(line)
            for line in path.read_text().splitlines()
            if line.strip()
        )
    }


def write_records(path: Path, records: dict[str, dict[str, Any]]) -> None:
    temporary = path.with_suffix(".jsonl.tmp")
    temporary.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in sorted(records.values(), key=lambda row: row["caseId"])
        )
    )
    temporary.replace(path)


def main() -> int:
    load_env(ROOT / ".env")
    load_env(ROOT.parents[1] / ".env")
    args = parse_args()
    os.environ["VLM_PROVIDER"] = args.provider
    if args.provider == "hf_router":
        os.environ.setdefault("HF_VLM_MODEL", "Qwen/Qwen3-VL-30B-A3B-Instruct")
        os.environ.setdefault("HF_ROUTER_MAX_TOKENS", "1400")
    os.environ.setdefault("MINIMAX_MAX_CALLS", "100")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    prepared_dir = args.output_dir / "runtime" / "prepared"
    output = args.output_dir / f"{args.provider}.jsonl"
    records = {} if args.force else read_records(output)
    pending = [case for case in CASES if case["id"] not in records]

    def analyze(case: dict[str, Any]) -> dict[str, Any]:
        image_paths = [
            prepare_image(args.source_dir / relative, prepared_dir, args.max_image_pixels)
            for relative in case["images"]
        ]
        result = call_vlm(
            SYSTEM,
            case["prompt"],
            image_paths,
            metadata={
                "caseId": case["id"],
                "kind": case["kind"],
                "sourceDate": case["sourceDate"],
                "datasetUrl": case["datasetUrl"],
                "sourceFiles": list(case["images"]),
            },
            review_type="mapaction_response_site_inventory",
        )
        return {
            "caseId": case["id"],
            "kind": case["kind"],
            "sourceDate": case["sourceDate"],
            "datasetUrl": case["datasetUrl"],
            "sourceFiles": list(case["images"]),
            "analysis": result,
            "publicationStatus": "documentary-map-extraction-requires-source-review",
        }

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        futures = {executor.submit(analyze, case): case["id"] for case in pending}
        for index, future in enumerate(as_completed(futures), 1):
            case_id = futures[future]
            try:
                records[case_id] = future.result()
            except Exception as exc:
                print(f"{args.provider} {case_id}: ERROR {exc}", flush=True)
                continue
            write_records(output, records)
            print(
                f"{args.provider} {index}/{len(pending)} {case_id}",
                flush=True,
            )

    usage: Counter[str] = Counter()
    for record in records.values():
        provider_usage = (
            record.get("analysis", {}).get("provider_usage") or {}
        )
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = provider_usage.get(key)
            if isinstance(value, (int, float)):
                usage[key] += value
    summary = {
        "version": 1,
        "provider": args.provider,
        "cases": len(CASES),
        "completed": len(records),
        "pending": len(CASES) - len(records),
        "usage": dict(usage),
        "output": str(output.relative_to(ROOT)),
        "guardrails": [
            "Map labels are documentary evidence as of the stated source date.",
            "Visual shelter counts are ranges, not capacity or occupancy figures.",
            "Missing labels do not prove absence.",
            "Source products remain external; this pipeline stores no republished map imagery.",
        ],
    }
    (args.output_dir / f"{args.provider}_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
