#!/usr/bin/env python3
"""Build public aggregate operational-signal cells.

The output is safe-by-design for the public app: no raw Kobo rows, WhatsApp
messages, exact report points, report text, links, names, phones, photos, or
addresses are written. Community reports are only shown when a grid cell passes
minimum k-anonymity and distinct-timestamp thresholds.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from shapely.geometry import shape


ROOT = Path(__file__).resolve().parents[1]
KOBO_URL = "https://kf.kobotoolbox.org/api/v2/assets/a8XWDsdUcpBzXGtgQmiiro/data.json"
CATALOG = ROOT / "public/data/catalog.json"
EXTERNAL_DETAIL = ROOT / "ops/data_acquisition_plan/external_prediction_official_overlap_detail.csv"
OUT_DIR = ROOT / "public/data/operational-signals"
WHATSAPP_CHAT_ENV = "OPERATIONAL_SIGNALS_WHATSAPP_CHAT"
GRID_DEGREES = 0.02
MIN_COMMUNITY_REPORTS = 5
MIN_DISTINCT_SUBMISSION_MINUTES = 3
MIN_EXTERNAL_GAP_CANDIDATES = 20

WHATSAPP_MESSAGE_RE = re.compile(
    r"^(?P<date>\d{1,2}/\d{1,2}/\d{2}),\s+"
    r"(?P<time>\d{1,2}:\d{2})\s*(?P<ampm>AM|PM|a\.m\.|p\.m\.)?\s+-\s+"
    r"(?P<sender>.*?):\s*(?P<text>.*)$",
    re.IGNORECASE,
)
DMS_PAIR_RE = re.compile(
    r"(?P<latd>\d{1,2})[°º]\s*(?P<latm>\d{1,2})['’]\s*(?P<lats>\d{1,2}(?:\.\d+)?)\"?\s*(?P<lathem>[NS])"
    r"\s+"
    r"(?P<lond>\d{1,3})[°º]\s*(?P<lonm>\d{1,2})['’]\s*(?P<lons>\d{1,2}(?:\.\d+)?)\"?\s*(?P<lonhem>[EW])",
    re.IGNORECASE,
)
DECIMAL_PAIR_RE = re.compile(r"(?<!\d)(?P<lat>1[0-4]\.\d{3,})\s*,?\s*(?P<lon>-[5-7]\d\.\d{3,})(?!\d)")


@dataclass
class Cell:
    key: str
    lat_idx: int
    lon_idx: int
    community_total_raw: int = 0
    community_events: Counter[str] = field(default_factory=Counter)
    community_time_buckets: set[str] = field(default_factory=set)
    latest_submission: str | None = None
    ems_official_destroyed_damaged: int = 0
    ems_official_possible: int = 0
    ems_monitor_destroyed_damaged: int = 0
    ems_monitor_possible: int = 0
    external_gap_candidates: int = 0
    aoi_ids: set[str] = field(default_factory=set)
    aoi_labels: set[str] = field(default_factory=set)

    @property
    def south(self) -> float:
        return self.lat_idx * GRID_DEGREES

    @property
    def north(self) -> float:
        return (self.lat_idx + 1) * GRID_DEGREES

    @property
    def west(self) -> float:
        return self.lon_idx * GRID_DEGREES

    @property
    def east(self) -> float:
        return (self.lon_idx + 1) * GRID_DEGREES

    @property
    def center_lat(self) -> float:
        return (self.south + self.north) / 2

    @property
    def center_lon(self) -> float:
        return (self.west + self.east) / 2


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_cell(cells: dict[str, Cell], lat: float, lon: float) -> Cell:
    lat_idx = math.floor(lat / GRID_DEGREES)
    lon_idx = math.floor(lon / GRID_DEGREES)
    key = f"z{lat_idx}_{lon_idx}"
    if key not in cells:
        cells[key] = Cell(key=key, lat_idx=lat_idx, lon_idx=lon_idx)
    return cells[key]


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def event_bucket(raw: str | None) -> str:
    value = (raw or "").lower()
    if "edificio" in value or "estructural" in value or "colaps" in value or "da_o" in value or "daño" in value:
        return "structural_damage"
    if "acopio" in value or "auxilio" in value or "primeros" in value:
        return "aid_collection_first_aid"
    if "agua" in value:
        return "water"
    if "salud" in value or "medic" in value:
        return "health"
    if "acceso" in value or "bloque" in value:
        return "access"
    return "other"


def fetch_kobo_minimal_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    url = f"{KOBO_URL}?limit=1000"
    while url:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        for raw in payload.get("results", []):
            geo = raw.get("_geolocation")
            lat = lon = None
            if isinstance(geo, list) and len(geo) >= 2:
                lat, lon = geo[0], geo[1]
            rows.append(
                {
                    "event": raw.get("Evento"),
                    "lat": lat,
                    "lon": lon,
                    "submitted_at": raw.get("_submission_time") or raw.get("end") or raw.get("start"),
                    "validation_status": raw.get("_validation_status") or {},
                }
            )
        url = payload.get("next")
    return rows


def add_kobo(cells: dict[str, Cell]) -> dict[str, Any]:
    rows = fetch_kobo_minimal_rows()
    event_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    mapped = 0
    for row in rows:
        status = row.get("validation_status") or {}
        validation_counts[str(status.get("label") or status.get("uid") or "unreviewed")] += 1
        event = event_bucket(row.get("event"))
        event_counts[event] += 1
        lat, lon = row.get("lat"), row.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        if not (0 <= lat <= 15 and -75 <= lon <= -55):
            continue
        mapped += 1
        cell = get_cell(cells, float(lat), float(lon))
        cell.community_total_raw += 1
        cell.community_events[event] += 1
        submitted = parse_dt(row.get("submitted_at"))
        if submitted:
            iso = submitted.isoformat().replace("+00:00", "Z")
            cell.community_time_buckets.add(iso[:16])
            if not cell.latest_submission or iso > cell.latest_submission:
                cell.latest_submission = iso
    return {
        "source": "Kobo public API",
        "records": len(rows),
        "mappedRecords": mapped,
        "eventCounts": dict(event_counts),
        "validationCounts": dict(validation_counts),
    }


def normalize_whatsapp_line(line: str) -> str:
    return line.replace("\u202f", " ").replace("\xa0", " ").strip("\n")


def parse_whatsapp_timestamp(date_value: str, time_value: str, ampm: str | None) -> str | None:
    suffix = (ampm or "").lower().replace(".", "")
    normalized_ampm = "AM" if suffix == "am" else "PM" if suffix == "pm" else ""
    raw = f"{date_value} {time_value} {normalized_ampm}".strip()
    for fmt in ("%m/%d/%y %I:%M %p", "%m/%d/%y %H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            return parsed.isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    return None


def dms_to_decimal(degrees: str, minutes: str, seconds: str, hemisphere: str) -> float:
    value = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    if hemisphere.upper() in {"S", "W"}:
        value *= -1
    return value


def extract_coordinates(text: str) -> tuple[float, float] | None:
    dms = DMS_PAIR_RE.search(text)
    if dms:
        lat = dms_to_decimal(dms["latd"], dms["latm"], dms["lats"], dms["lathem"])
        lon = dms_to_decimal(dms["lond"], dms["lonm"], dms["lons"], dms["lonhem"])
        return lat, lon
    decimal = DECIMAL_PAIR_RE.search(text)
    if decimal:
        return float(decimal["lat"]), float(decimal["lon"])
    return None


def parse_whatsapp_minimal_rows(path: Path) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in path.read_text(errors="replace").splitlines():
        line = normalize_whatsapp_line(raw_line)
        match = WHATSAPP_MESSAGE_RE.match(line)
        if match:
            if current:
                messages.append(current)
            current = {
                "text": match["text"],
                "submitted_at": parse_whatsapp_timestamp(match["date"], match["time"], match["ampm"]),
            }
            continue
        if current and line:
            current["text"] = f"{current['text']}\n{line}"
    if current:
        messages.append(current)

    rows: list[dict[str, Any]] = []
    for message in messages:
        text = str(message.get("text") or "")
        coords = extract_coordinates(text)
        rows.append(
            {
                "event": event_bucket(text),
                "lat": coords[0] if coords else None,
                "lon": coords[1] if coords else None,
                "submitted_at": message.get("submitted_at"),
                "has_coordinates": bool(coords),
            }
        )
    return rows


def add_whatsapp(cells: dict[str, Cell]) -> dict[str, Any]:
    configured_path = os.environ.get(WHATSAPP_CHAT_ENV)
    if not configured_path:
        return {
            "source": "local WhatsApp chat export",
            "configured": False,
            "records": 0,
            "mappedRecords": 0,
            "coordinateMessages": 0,
            "eventCounts": {},
        }
    path = Path(configured_path).expanduser()
    if not path.exists() or not path.is_file():
        return {
            "source": "local WhatsApp chat export",
            "configured": True,
            "status": "missing",
            "records": 0,
            "mappedRecords": 0,
            "coordinateMessages": 0,
            "eventCounts": {},
        }
    rows = parse_whatsapp_minimal_rows(path)
    event_counts: Counter[str] = Counter()
    mapped = 0
    coordinate_messages = 0
    for row in rows:
        event = str(row.get("event") or "other")
        event_counts[event] += 1
        lat, lon = row.get("lat"), row.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            continue
        coordinate_messages += 1
        if not (0 <= lat <= 15 and -75 <= lon <= -55):
            continue
        mapped += 1
        cell = get_cell(cells, float(lat), float(lon))
        cell.community_total_raw += 1
        cell.community_events[event] += 1
        submitted = parse_dt(row.get("submitted_at"))
        if submitted:
            iso = submitted.isoformat().replace("+00:00", "Z")
            cell.community_time_buckets.add(iso[:16])
            if not cell.latest_submission or iso > cell.latest_submission:
                cell.latest_submission = iso
    return {
        "source": "local WhatsApp chat export",
        "configured": True,
        "records": len(rows),
        "mappedRecords": mapped,
        "coordinateMessages": coordinate_messages,
        "eventCounts": dict(event_counts),
    }


def load_catalog() -> list[dict[str, Any]]:
    return json.loads(CATALOG.read_text()).get("aois", [])


def localized_name(aoi: dict[str, Any]) -> str:
    value = aoi.get("name") or aoi.get("title") or aoi.get("id") or "AOI"
    if isinstance(value, dict):
        return str(value.get("es") or value.get("en") or aoi.get("id") or "AOI")
    return str(value)


def add_aoi_hint(cell: Cell, aois: list[dict[str, Any]]) -> None:
    for aoi in aois:
        bounds = aoi.get("bounds")
        if not bounds or len(bounds) != 2:
            continue
        south, west = bounds[0]
        north, east = bounds[1]
        if south <= cell.center_lat <= north and west <= cell.center_lon <= east:
            cell.aoi_ids.add(str(aoi.get("id")))
            label = localized_name(aoi).replace(" - Vector oficial EMSR884", "").replace(" - Official EMSR884 Vector", "")
            cell.aoi_labels.add(label)


def damage_class(props: dict[str, Any]) -> str:
    raw = str(props.get("damage_class") or props.get("damage_gra") or props.get("DMG_GRADING") or "").lower()
    if "destroy" in raw:
        return "destroyed"
    if raw == "damaged" or ("damaged" in raw and "possibly" not in raw):
        return "damaged"
    if "possib" in raw:
        return "possible"
    return "unknown"


def feature_centroid(feature: dict[str, Any]) -> tuple[float, float] | None:
    props = feature.get("properties") or {}
    lat = props.get("centroid_lat")
    lon = props.get("centroid_lon")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        return float(lat), float(lon)
    try:
        centroid = shape(feature["geometry"]).centroid
    except Exception:
        return None
    return float(centroid.y), float(centroid.x)


def add_ems(cells: dict[str, Cell], aois: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for aoi in aois:
        if aoi.get("status") == "external-prediction":
            continue
        damage_ref = (aoi.get("layers") or {}).get("damage")
        if not damage_ref or not str(damage_ref).startswith("/data/"):
            continue
        path = ROOT / "public" / str(damage_ref).lstrip("/")
        if not path.exists():
            continue
        status = str(aoi.get("status") or "")
        is_monitor = status == "official-monitor-points" or "monitor01" in str(aoi.get("id"))
        data = json.loads(path.read_text())
        for feature in data.get("features", []):
            centroid = feature_centroid(feature)
            if not centroid:
                continue
            cell = get_cell(cells, centroid[0], centroid[1])
            cls = damage_class(feature.get("properties") or {})
            if is_monitor:
                if cls in {"destroyed", "damaged"}:
                    cell.ems_monitor_destroyed_damaged += 1
                elif cls == "possible":
                    cell.ems_monitor_possible += 1
            else:
                if cls in {"destroyed", "damaged"}:
                    cell.ems_official_destroyed_damaged += 1
                elif cls == "possible":
                    cell.ems_official_possible += 1
            counts[f"{status}:{cls}"] += 1
    return dict(counts)


def add_external_gaps(cells: dict[str, Cell]) -> dict[str, Any]:
    if not EXTERNAL_DETAIL.exists():
        return {"status": "missing"}
    total = 0
    outside = 0
    with EXTERNAL_DETAIL.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total += 1
            if str(row.get("overlaps_official_gra")).lower() != "false":
                continue
            try:
                lat = float(row["centroid_lat"])
                lon = float(row["centroid_lon"])
            except (KeyError, TypeError, ValueError):
                continue
            outside += 1
            get_cell(cells, lat, lon).external_gap_candidates += 1
    return {"detailRows": total, "outsideOfficialGraRows": outside}


def community_is_public(cell: Cell) -> bool:
    return (
        cell.community_total_raw >= MIN_COMMUNITY_REPORTS
        and len(cell.community_time_buckets) >= MIN_DISTINCT_SUBMISSION_MINUTES
    )


def priority_for(cell: Cell) -> tuple[str, int, list[str]]:
    safe_reports = cell.community_total_raw if community_is_public(cell) else 0
    structural = cell.community_events.get("structural_damage", 0) if safe_reports else 0
    official = cell.ems_official_destroyed_damaged
    external = cell.external_gap_candidates if cell.external_gap_candidates >= MIN_EXTERNAL_GAP_CANDIDATES else 0
    score = 0
    reasons: list[str] = []
    if safe_reports:
        score += min(40, safe_reports * 2)
        reasons.append(f"{safe_reports} aggregated community reports")
    if structural:
        score += min(30, structural * 3)
        reasons.append(f"{structural} structural-damage reports")
    if official:
        score += min(25, official * 2)
        reasons.append(f"{official} official EMS destroyed/damaged features")
    if external:
        score += min(30, max(8, external // 4))
        reasons.append(f"{external} external candidates outside GRA")
    if structural >= 5 and official == 0:
        score += 25
        reasons.append("gap: community structural reports without GRA damage in this cell")
    if external >= 50 and official == 0:
        score += 20
        reasons.append("gap: dense external candidates outside GRA")
    if score >= 70:
        return "high", score, reasons
    if score >= 35:
        return "medium", score, reasons
    return "low", score, reasons


def polygon_for(cell: Cell) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[
            [cell.west, cell.south],
            [cell.east, cell.south],
            [cell.east, cell.north],
            [cell.west, cell.north],
            [cell.west, cell.south],
        ]],
    }


def visible_properties(cell: Cell, sequence: int, aois: list[dict[str, Any]]) -> dict[str, Any] | None:
    safe_reports = community_is_public(cell)
    external_visible = cell.external_gap_candidates >= MIN_EXTERNAL_GAP_CANDIDATES
    ems_visible = (
        cell.ems_official_destroyed_damaged
        + cell.ems_official_possible
        + cell.ems_monitor_destroyed_damaged
        + cell.ems_monitor_possible
    ) > 0
    if not safe_reports and not external_visible and not ems_visible:
        return None
    add_aoi_hint(cell, aois)
    priority, score, reasons = priority_for(cell)
    community_events = {
        key: int(value)
        for key, value in cell.community_events.items()
        if safe_reports and value > 0
    }
    return {
        "id": f"ops-zone-{sequence:03d}",
        "priority": priority,
        "score": score,
        "communityReports": int(cell.community_total_raw) if safe_reports else None,
        "communityReportsSuppressed": not safe_reports and cell.community_total_raw > 0,
        "communityEvents": community_events,
        "latestSubmissionDate": cell.latest_submission[:10] if safe_reports and cell.latest_submission else None,
        "emsOfficialDestroyedDamaged": cell.ems_official_destroyed_damaged,
        "emsOfficialPossible": cell.ems_official_possible,
        "emsMonitorDestroyedDamaged": cell.ems_monitor_destroyed_damaged,
        "emsMonitorPossible": cell.ems_monitor_possible,
        "externalGapCandidates": cell.external_gap_candidates if external_visible else None,
        "externalGapSuppressed": not external_visible and cell.external_gap_candidates > 0,
        "aoiIds": sorted(cell.aoi_ids),
        "aoiLabels": sorted(cell.aoi_labels)[:3],
        "reasons": reasons[:4],
        "publicNote": "Aggregate zone only; no raw reports, exact points, names, phones, links, photos, or addresses.",
    }


def build_geojson(cells: dict[str, Cell], aois: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    ordered = sorted(
        cells.values(),
        key=lambda cell: (
            {"high": 0, "medium": 1, "low": 2}[priority_for(cell)[0]],
            -priority_for(cell)[1],
            -cell.community_total_raw,
            -cell.external_gap_candidates,
        ),
    )
    features: list[dict[str, Any]] = []
    for sequence, cell in enumerate(ordered, start=1):
        props = visible_properties(cell, sequence, aois)
        if not props:
            continue
        features.append({"type": "Feature", "properties": props, "geometry": polygon_for(cell)})
    return {
        "type": "FeatureCollection",
        "metadata": {
            "status": "public-aggregate-not-official-damage",
            "generatedAt": generated_at,
            "gridDegrees": GRID_DEGREES,
            "minCommunityReports": MIN_COMMUNITY_REPORTS,
            "minDistinctSubmissionMinutes": MIN_DISTINCT_SUBMISSION_MINUTES,
            "minExternalGapCandidates": MIN_EXTERNAL_GAP_CANDIDATES,
            "warning": "Operational signals are triage guidance only. EMS remains the official source of damage counts.",
        },
        "features": features,
    }


def main() -> int:
    generated_at = now_utc()
    cells: dict[str, Cell] = {}
    aois = load_catalog()
    kobo = add_kobo(cells)
    whatsapp = add_whatsapp(cells)
    ems = add_ems(cells, aois)
    external = add_external_gaps(cells)
    geojson = build_geojson(cells, aois, generated_at)
    priority_counts = Counter(feature["properties"]["priority"] for feature in geojson["features"])
    summary = {
        "status": "public-aggregate-not-official-damage",
        "generatedAt": generated_at,
        "privacy": {
            "rawKoboWritten": False,
            "rawWhatsappWritten": False,
            "exactReportPointsWritten": False,
            "freeTextWritten": False,
            "minCommunityReportsPerVisibleCell": MIN_COMMUNITY_REPORTS,
            "minDistinctSubmissionMinutesPerVisibleCell": MIN_DISTINCT_SUBMISSION_MINUTES,
            "gridDegrees": GRID_DEGREES,
        },
        "kobo": kobo,
        "whatsapp": whatsapp,
        "emsCounts": ems,
        "externalGap": external,
        "visibleCells": len(geojson["features"]),
        "priorityCounts": dict(priority_counts),
        "warning": "Community, VLM, and external prediction signals are triage only and must not be counted as official EMS damage.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cells.geojson").write_text(json.dumps(geojson, ensure_ascii=False, indent=2) + "\n")
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
