#!/usr/bin/env python3
"""Build one lightweight evidence-detail document per full-pilot candidate cell."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RECONSTRUCTION = ROOT / "public" / "data" / "reconstruction"
OBSERVATIONS = RECONSTRUCTION / "full-pilot-response-evidence.jsonl"
CROPS = RECONSTRUCTION / "full-pilot-response-evidence-crops.jsonl"
SUMMARY = RECONSTRUCTION / "full-pilot-response-evidence-summary.json"
OUTPUT = RECONSTRUCTION / "full-pilot-evidence-cells"
EXPLORER_SUMMARY = (
    RECONSTRUCTION / "full-pilot-evidence-explorer-summary.json"
)
SAFE_CELL_ID = re.compile(r"^pilot_r\d{3}_c\d{3}$")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def main() -> int:
    observations = read_jsonl(OBSERVATIONS)
    pairs = read_jsonl(CROPS)
    summary = json.loads(SUMMARY.read_text())
    observations_by_cell = {row["cellId"]: row for row in observations}
    pairs_by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for pair in pairs:
        cell_id = str(pair.get("cellId") or "")
        if cell_id not in observations_by_cell:
            raise SystemExit(f"Crop pair references unknown candidate cell: {cell_id}")
        pairs_by_cell[cell_id].append(pair)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    expected_files: set[Path] = set()
    for cell_id, observation in observations_by_cell.items():
        if not SAFE_CELL_ID.fullmatch(cell_id):
            raise SystemExit(f"Unsafe or unexpected cell id: {cell_id}")
        detail_path = OUTPUT / f"{cell_id}.json"
        expected_files.add(detail_path)
        cell_pairs = sorted(
            pairs_by_cell.get(cell_id, []),
            key=lambda row: (
                int(row.get("rank") or 999999),
                str(row.get("pairId") or ""),
            ),
        )
        payload = {
            "version": 1,
            "updatedAt": summary["updatedAt"],
            "publicationStatus": "ai-triage-native-review-required",
            "observation": observation,
            "evidencePairs": cell_pairs,
            "pairCount": len(cell_pairs),
            "policy": {
                "nativePixels": (
                    "Native crops are the evidence view. Enhanced images are "
                    "display-only and cannot establish a feature."
                ),
                "arrival": summary["method"]["arrivalRule"],
                "absence": summary["method"]["absenceRule"],
            },
        }
        detail_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        )

    for stale_path in OUTPUT.glob("*.json"):
        if stale_path not in expected_files:
            stale_path.unlink()

    compact_summary = {
        key: value
        for key, value in summary.items()
        if key != "topObservations"
    }
    compact_summary["explorer"] = {
        "observationIndex": "/data/reconstruction/full-pilot-response-evidence.jsonl",
        "cellDetailBase": "/data/reconstruction/full-pilot-evidence-cells",
        "candidateCells": len(observations),
        "detailFiles": len(expected_files),
        "cropPairs": len(pairs),
    }
    EXPLORER_SUMMARY.write_text(
        json.dumps(
            compact_summary,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
    )

    missing_pairs = [
        pair_id
        for observation in observations
        for pair_id in observation.get("cropPairIds") or []
        if not any(
            pair.get("pairId") == pair_id
            for pair in pairs_by_cell.get(observation["cellId"], [])
        )
    ]
    if missing_pairs:
        raise SystemExit(
            f"Candidate observations reference {len(missing_pairs)} missing crop pairs"
        )

    print(
        json.dumps(
            {
                "result": "pass",
                "candidateCells": len(observations),
                "detailFiles": len(expected_files),
                "cropPairs": len(pairs),
                "compactSummaryBytes": EXPLORER_SUMMARY.stat().st_size,
                "output": str(OUTPUT.relative_to(ROOT)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
