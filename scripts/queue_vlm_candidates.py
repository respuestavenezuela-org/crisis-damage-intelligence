#!/usr/bin/env python3
"""Create a prioritized VLM review queue JSONL from a damage GeoJSON.

This does not call a model. It produces an auditable queue that a batch runner can
consume later. Priority is intentionally conservative:
  10: Destroyed/Damaged official EMS features
  30: Possibly damaged official EMS features
  90: everything else
"""
import json
import sys
from pathlib import Path


def priority_for(props: dict) -> int:
    raw = str(props.get("damage_gra") or props.get("damage_class") or "").lower()
    if "destroy" in raw or raw == "damaged":
        return 10
    if "possibly" in raw or "possible" in raw:
        return 30
    return 90


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: scripts/queue_vlm_candidates.py AOI_ID DAMAGE_GEOJSON OUT_JSONL")
    aoi_id, geojson_path, out_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    data = json.loads(geojson_path.read_text())
    rows = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        rows.append(
            {
                "aoi_id": aoi_id,
                "feature_id": props.get("id"),
                "priority": priority_for(props),
                "status": "queued",
                "damage_gra": props.get("damage_gra"),
                "google_maps_url": props.get("google_maps_url"),
                "model": None,
                "reason": "official EMS label priority; model not yet run",
            }
        )
    rows.sort(key=lambda row: (row["priority"], row["feature_id"] or ""))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n")
    print(f"Wrote {len(rows)} VLM queue rows to {out_path}")


if __name__ == "__main__":
    main()
