#!/usr/bin/env python3
"""Build a deterministic human-review queue from all reconstruction packets."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data" / "reconstruction"
CATALOG_PATH = DATA_DIR / "catalog.json"
AERIAL_EVIDENCE_PATH = DATA_DIR / "aerial-response-evidence-la-guaira.json"
OUT_DIR = ROOT / "ops" / "reconstruction"
OUT_JSON = OUT_DIR / "review_queue.json"
OUT_MD = OUT_DIR / "review_queue.md"

CONFIDENCE_PRIORITY = {
    "inferred": 0,
    "single-source": 1,
    "corroborated": 2,
    "confirmed": 3,
}


def load_packet(data_path: str) -> dict[str, Any]:
    path = ROOT / "public" / data_path.lstrip("/")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    aerial_evidence = json.loads(AERIAL_EVIDENCE_PATH.read_text(encoding="utf-8"))
    queue: list[dict[str, Any]] = []

    for entry in catalog["entries"]:
        if entry["status"] != "published":
            continue
        packet = load_packet(entry["dataPath"])
        for gap_index, gap in enumerate(entry.get("gaps", []), start=1):
            queue.append({
                "id": f"{entry['slug']}-gap-{gap_index:02d}",
                "packet": entry["slug"],
                "kind": "coverage-gap",
                "priority": entry["priority"] * 10,
                "confidence": None,
                "title": gap,
                "sourceIds": [],
                "status": "open",
                "reviewQuestion": {
                    "es": "¿Existe evidencia fechada y situada que cierre esta brecha sin inferir ausencia?",
                    "en": "Is there dated, situated evidence that closes this gap without inferring absence?"
                }
            })

        for kind, records in (
            ("first72-finding", packet["first72Assessment"]["findings"]),
            ("timeline-event", packet["events"]),
        ):
            for record in records:
                confidence = record["confidence"]
                if confidence not in {"inferred", "single-source"}:
                    continue
                queue.append({
                    "id": f"{entry['slug']}-{kind}-{record['id']}",
                    "packet": entry["slug"],
                    "kind": kind,
                    "priority": entry["priority"] * 10 + CONFIDENCE_PRIORITY[confidence],
                    "confidence": confidence,
                    "title": record["title"],
                    "sourceIds": record["sourceIds"],
                    "status": "open",
                    "reviewQuestion": {
                        "es": "¿Puede una fuente independiente, primaria o visual aumentar o reducir esta confianza?",
                        "en": "Can an independent, primary or visual source raise or lower this confidence?"
                    }
                })

        if entry["slug"] == "la-guaira":
            for observation in aerial_evidence["observations"]:
                queue.append({
                    "id": f"la-guaira-aerial-observation-{observation['chipId']}",
                    "packet": "la-guaira",
                    "kind": "aerial-observation",
                    "priority": entry["priority"] * 10,
                    "confidence": observation["confidence"],
                    "title": observation["title"],
                    "sourceIds": observation["sourceIds"],
                    "status": "open",
                    "reviewQuestion": {
                        "es": "¿Puede otra adquisición fechada o evidencia de campo confirmar el tipo, llegada y uso del objeto sin depender de la mejora 2×?",
                        "en": "Can another dated acquisition or field evidence confirm the object's type, arrival and use without relying on the 2× enhancement?"
                    }
                })

    queue.sort(key=lambda item: (item["priority"], item["packet"], item["kind"], item["id"]))
    payload = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "itemCount": len(queue),
        "openCount": sum(item["status"] == "open" for item in queue),
        "items": queue,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Reconstruction review queue",
        "",
        f"Generated: {payload['generatedAt']}",
        f"Open items: {payload['openCount']}",
        "",
        "| Priority | Packet | Kind | Confidence | Review item |",
        "|---:|---|---|---|---|",
    ]
    for item in queue:
        lines.append(
            f"| {item['priority']} | {item['packet']} | {item['kind']} | "
            f"{item['confidence'] or 'n/a'} | {item['title']['en']} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Review queue built: {payload['openCount']} open items -> {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
