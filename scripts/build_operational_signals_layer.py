#!/usr/bin/env python3
"""Build public aggregate operational-signal zones.

The output is safe-by-design for the public app: no raw Kobo rows, WhatsApp
messages, exact report points, report text, links, names, phones, photos, or
addresses are written. Community reports are only shown when an aggregate zone
passes minimum k-anonymity and distinct-timestamp thresholds.
"""

from __future__ import annotations

import csv
import json
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from shapely.geometry import Point, mapping, shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
KOBO_URL = "https://kf.kobotoolbox.org/api/v2/assets/a8XWDsdUcpBzXGtgQmiiro/data.json"
CATALOG = ROOT / "public/data/catalog.json"
EXTERNAL_DETAIL = ROOT / "ops/data_acquisition_plan/external_prediction_official_overlap_detail.csv"
OUT_DIR = ROOT / "public/data/operational-signals"
WHATSAPP_CHAT_ENV = "OPERATIONAL_SIGNALS_WHATSAPP_CHAT"
KOBO_MAX_PAGES = 100
IMPACT_ENVELOPE_BUFFER_DEGREES = 0.0035
IMPACT_ENVELOPE_INSET_DEGREES = 0.0012
IMPACT_ENVELOPE_SIMPLIFY_DEGREES = 0.00035
IMPACT_ENVELOPE_MIN_AREA_DEGREES = 0.000002
IMPACT_BASE_STATUSES = {
    "official-vector",
    "official-monitor-points",
    "external-gap",
    "external-prediction",
}
IMPACT_OVERLAP_POLICY = "source_precedence_non_overlapping"
IMPACT_SOURCE_PRECEDENCE = {
    "official-ems": 0,
    "monit01": 1,
    "external-gap": 2,
    "external-prediction": 2,
    "community-aggregate": 3,
}
MIN_COMMUNITY_REPORTS = 8
MIN_DISTINCT_SUBMISSION_MINUTES = 5
MIN_EXTERNAL_GAP_CANDIDATES = 20
OFFICIAL_IMPACT_NOTE = (
    "Operational impact envelope derived from official EMS damaged/possibly damaged feature geometry. "
    "Counts remain EMS source-of-record; community, MONIT01, VLM, and external signals are triage only."
)
MONITOR_IMPACT_NOTE = (
    "Operational impact envelope derived from MONIT01 point geometry where no matching GRA vector envelope is published. "
    "MONIT01 remains separate from official GRA counts."
)
EXTERNAL_IMPACT_NOTE = (
    "Operational triage envelope derived from external visual gap polygons outside official GRA. "
    "Not an official EMS damage area."
)
EXTERNAL_PREDICTION_IMPACT_NOTE = (
    "Operational triage envelope derived from Microsoft AI4G prediction geometry outside official GRA. "
    "External predictions are not official EMS damage labels or counts."
)

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
DECIMAL_PAIR_RE = re.compile(r"(?<!\d)(?P<lat>\d{1,2}\.\d{3,})\s*,?\s*(?P<lon>-[5-7]\d\.\d{3,})(?!\d)")


@dataclass
class SignalObservation:
    lat: float
    lon: float
    kind: str
    event: str | None = None
    submitted_at: str | None = None
    damage: str | None = None
    aoi_id: str | None = None
    aoi_label: str | None = None


@dataclass
class Zone:
    sector_id: str | None = None
    sector_label: str | None = None
    sector_row: int | None = None
    sector_col: int | None = None
    geometry: Any | None = None
    public_geometry: Any | None = None
    geometry_method: str = "evidence_impact_envelope"
    geometry_source: str = "official-ems"
    public_note: str = OFFICIAL_IMPACT_NOTE
    observations: list[SignalObservation] = field(default_factory=list)
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

    def add(self, observation: SignalObservation) -> None:
        self.observations.append(observation)
        if observation.aoi_id:
            self.aoi_ids.add(observation.aoi_id)
        if observation.aoi_label:
            self.aoi_labels.add(observation.aoi_label)
        if observation.kind == "community":
            self.community_total_raw += 1
            if observation.event:
                self.community_events[observation.event] += 1
            submitted = parse_dt(observation.submitted_at)
            if submitted:
                iso = submitted.isoformat().replace("+00:00", "Z")
                self.community_time_buckets.add(iso[:16])
                if not self.latest_submission or iso > self.latest_submission:
                    self.latest_submission = iso
        elif observation.kind == "ems_official":
            if observation.damage in {"destroyed", "damaged"}:
                self.ems_official_destroyed_damaged += 1
            elif observation.damage == "possible":
                self.ems_official_possible += 1
        elif observation.kind == "ems_monitor":
            if observation.damage in {"destroyed", "damaged"}:
                self.ems_monitor_destroyed_damaged += 1
            elif observation.damage == "possible":
                self.ems_monitor_possible += 1
        elif observation.kind == "external_gap":
            self.external_gap_candidates += 1


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def valid_venezuela_coordinate(lat: Any, lon: Any) -> bool:
    return isinstance(lat, (int, float)) and isinstance(lon, (int, float)) and 0 <= lat <= 15 and -75 <= lon <= -55


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
    pages = 0
    while url:
        pages += 1
        if pages > KOBO_MAX_PAGES:
            raise RuntimeError(f"Kobo pagination exceeded {KOBO_MAX_PAGES} pages")
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


def add_kobo(observations: list[SignalObservation]) -> dict[str, Any]:
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
        if not valid_venezuela_coordinate(lat, lon):
            continue
        mapped += 1
        submitted = parse_dt(row.get("submitted_at"))
        observations.append(SignalObservation(
            lat=float(lat),
            lon=float(lon),
            kind="community",
            event=event,
            submitted_at=submitted.isoformat().replace("+00:00", "Z") if submitted else None,
        ))
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


def add_whatsapp(observations: list[SignalObservation]) -> dict[str, Any]:
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
        if not valid_venezuela_coordinate(lat, lon):
            continue
        mapped += 1
        submitted = parse_dt(row.get("submitted_at"))
        observations.append(SignalObservation(
            lat=float(lat),
            lon=float(lon),
            kind="community",
            event=event,
            submitted_at=submitted.isoformat().replace("+00:00", "Z") if submitted else None,
        ))
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


def aoi_label(aoi: dict[str, Any]) -> str:
    return localized_name(aoi).replace(" - Vector oficial EMSR884", "").replace(" - Official EMSR884 Vector", "")


def short_aoi_label(aoi: dict[str, Any]) -> str:
    return re.sub(r"^AOI\d+\s+", "", aoi_label(aoi))


def should_build_impact_aoi(aoi: dict[str, Any]) -> bool:
    status = str(aoi.get("status") or "")
    if status not in IMPACT_BASE_STATUSES:
        return False
    damage_ref = (aoi.get("layers") or {}).get("damage")
    return bool(damage_ref and str(damage_ref).startswith("/data/"))


def impact_geometry_context(aoi: dict[str, Any]) -> tuple[str, str, str, str]:
    status = str(aoi.get("status") or "")
    if status == "external-gap":
        return "external_gap_impact_envelope", "external-gap", EXTERNAL_IMPACT_NOTE, "Zona triage externo"
    if status == "external-prediction":
        return (
            "external_prediction_impact_envelope",
            "external-prediction",
            EXTERNAL_PREDICTION_IMPACT_NOTE,
            "Zona predicción externa",
        )
    if status == "official-monitor-points":
        return "monitor_triage_impact_envelope", "monit01", MONITOR_IMPACT_NOTE, "Zona MONIT01"
    return "official_ems_impact_envelope", "official-ems", OFFICIAL_IMPACT_NOTE, "Zona de impacto"


def load_aoi_damage_geometries(aoi: dict[str, Any]) -> list[Any]:
    damage_ref = (aoi.get("layers") or {}).get("damage")
    if not damage_ref or not str(damage_ref).startswith("/data/"):
        return []
    path = ROOT / "public" / str(damage_ref).lstrip("/")
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    geometries: list[Any] = []
    for feature in data.get("features", []):
        raw_geometry = feature.get("geometry")
        if not raw_geometry:
            continue
        try:
            geometry = shape(raw_geometry)
        except Exception:
            continue
        if geometry.is_empty:
            continue
        cls = damage_class(feature.get("properties") or {})
        if str(aoi.get("status") or "") == "official-vector" and cls == "unknown":
            continue
        geometries.append(geometry)
    return geometries


def polygon_parts(geometry: Any) -> list[Any]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    if geometry.geom_type == "GeometryCollection":
        parts: list[Any] = []
        for item in geometry.geoms:
            parts.extend(polygon_parts(item))
        return parts
    return []


def impact_envelopes(source_geometries: list[Any]) -> list[Any]:
    buffered = []
    for geometry in source_geometries:
        try:
            expanded = geometry.buffer(IMPACT_ENVELOPE_BUFFER_DEGREES)
        except Exception:
            continue
        if not expanded.is_empty:
            buffered.append(expanded)
    if not buffered:
        return []
    union = unary_union(buffered)
    envelope = union.buffer(-IMPACT_ENVELOPE_INSET_DEGREES)
    if envelope.is_empty:
        envelope = union
    envelope = envelope.simplify(IMPACT_ENVELOPE_SIMPLIFY_DEGREES, preserve_topology=True)
    parts = []
    for polygon in polygon_parts(envelope):
        if polygon.area < IMPACT_ENVELOPE_MIN_AREA_DEGREES:
            continue
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if not polygon.is_empty:
            parts.append(polygon)
    return sorted(parts, key=lambda item: (-item.area, item.bounds[0], item.bounds[1]))


def source_precedence(zone: Zone) -> int:
    return IMPACT_SOURCE_PRECEDENCE.get(zone.geometry_source, 99)


def polygonal_geometry(geometry: Any) -> Any | None:
    parts = []
    for polygon in polygon_parts(geometry):
        if polygon.area < IMPACT_ENVELOPE_MIN_AREA_DEGREES:
            continue
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        if not polygon.is_empty:
            parts.append(polygon)
    if not parts:
        return None
    merged = unary_union(parts)
    if not merged.is_valid:
        merged = merged.buffer(0)
    if merged.is_empty:
        return None
    return merged


def make_non_overlapping_impact_zones(zones: list[Zone]) -> list[Zone]:
    """Publish one operational surface: higher-confidence sources own the overlap."""
    ordered = sorted(
        zones,
        key=lambda zone: (
            source_precedence(zone),
            -(zone.geometry.area if zone.geometry is not None else 0),
            zone.sector_id or "",
        ),
    )
    claimed_geometries: list[Any] = []
    for zone in ordered:
        if zone.geometry is None or zone.geometry.is_empty:
            continue
        geometry = zone.geometry
        if claimed_geometries:
            claimed = unary_union(claimed_geometries)
            geometry = geometry.difference(claimed)
        public_geometry = polygonal_geometry(geometry)
        if public_geometry is None:
            continue
        zone.public_geometry = public_geometry
        claimed_geometries.append(public_geometry)
    return zones


def build_impact_zones(aois: list[dict[str, Any]]) -> list[Zone]:
    zones: list[Zone] = []
    for aoi in aois:
        if not should_build_impact_aoi(aoi):
            continue
        source_geometries = load_aoi_damage_geometries(aoi)
        envelopes = impact_envelopes(source_geometries)
        if not envelopes:
            continue
        geometry_method, geometry_source, public_note, label_prefix = impact_geometry_context(aoi)
        label = short_aoi_label(aoi)
        for index, geometry in enumerate(envelopes, start=1):
            zone = Zone(
                sector_id=f"{aoi.get('id')}-impact-{index:02d}",
                sector_label=f"{label} · {label_prefix} {index}",
                sector_row=None,
                sector_col=None,
                geometry=geometry,
                geometry_method=geometry_method,
                geometry_source=geometry_source,
                public_note=public_note,
            )
            zone.aoi_ids.add(str(aoi.get("id")))
            zone.aoi_labels.add(aoi_label(aoi))
            zones.append(zone)
    return make_non_overlapping_impact_zones(zones)


def best_sector_for_observation(observation: SignalObservation, zones: list[Zone]) -> Zone | None:
    point = Point(observation.lon, observation.lat)
    containing = [
        zone
        for zone in zones
        if zone.public_geometry is not None and zone.public_geometry.covers(point)
    ]
    if containing:
        best_precedence = min(source_precedence(zone) for zone in containing)
        candidates = [zone for zone in containing if source_precedence(zone) == best_precedence]
        if observation.aoi_id:
            matching_source = [zone for zone in candidates if observation.aoi_id in zone.aoi_ids]
            if matching_source:
                candidates = matching_source
        return min(
            candidates,
            key=lambda zone: zone.public_geometry.area if zone.public_geometry is not None else float("inf"),
        )
    return None


def assign_observations_to_sector_zones(observations: list[SignalObservation], zones: list[Zone]) -> dict[str, int]:
    stats: Counter[str] = Counter()
    for observation in observations:
        zone = best_sector_for_observation(observation, zones)
        if not zone:
            stats["droppedOutsideSectors"] += 1
            stats[f"dropped:{observation.kind}"] += 1
            continue
        zone.add(observation)
        stats["assigned"] += 1
        stats[f"assigned:{observation.kind}"] += 1
    return dict(stats)


def add_aoi_hint(zone: Zone, aois: list[dict[str, Any]], geometry: Any) -> None:
    point = geometry.representative_point()
    for aoi in aois:
        bounds = aoi.get("bounds")
        if not bounds or len(bounds) != 2:
            continue
        south, west = bounds[0]
        north, east = bounds[1]
        if south <= point.y <= north and west <= point.x <= east:
            zone.aoi_ids.add(str(aoi.get("id")))
            zone.aoi_labels.add(aoi_label(aoi))


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


def add_ems(observations: list[SignalObservation], aois: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for aoi in aois:
        status = str(aoi.get("status") or "")
        if status not in {"official-vector", "official-monitor-points"}:
            continue
        damage_ref = (aoi.get("layers") or {}).get("damage")
        if not damage_ref or not str(damage_ref).startswith("/data/"):
            continue
        path = ROOT / "public" / str(damage_ref).lstrip("/")
        if not path.exists():
            continue
        is_monitor = status == "official-monitor-points"
        kind = "ems_monitor" if is_monitor else "ems_official"
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            counts[f"{status}:read_error"] += 1
            continue
        for feature in data.get("features", []):
            centroid = feature_centroid(feature)
            if not centroid:
                continue
            cls = damage_class(feature.get("properties") or {})
            observations.append(SignalObservation(
                lat=centroid[0],
                lon=centroid[1],
                kind=kind,
                damage=cls,
                aoi_id=str(aoi.get("id")),
                aoi_label=aoi_label(aoi),
            ))
            counts[f"{status}:{cls}"] += 1
    return dict(counts)


def external_prediction_aoi_id(row: dict[str, str]) -> str | None:
    layer_name = str(row.get("layer_name") or "").lower()
    source_name = str(row.get("source_name") or "").lower()
    if "caraballeda" in layer_name:
        return "external-msft-caraballeda-east-predicted-damage"
    if "east-catia-la-mar" in layer_name:
        return "external-msft-catia-la-mar-east-predicted-damage"
    if "catia_la_mar_maxar" in layer_name:
        return "external-msft-catia-la-mar-predicted-damage"
    if layer_name == "out" or "la guaira" in source_name:
        return "external-msft-la-guaira-east-predicted-damage"
    return None


def add_external_gaps(observations: list[SignalObservation], aois: list[dict[str, Any]]) -> dict[str, Any]:
    if not EXTERNAL_DETAIL.exists():
        return {"status": "missing"}
    aoi_by_id = {str(aoi.get("id")): aoi for aoi in aois}
    total = 0
    outside = 0
    mapped_to_aoi = 0
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
            aoi_id = external_prediction_aoi_id(row)
            aoi = aoi_by_id.get(aoi_id or "")
            if aoi:
                mapped_to_aoi += 1
            observations.append(SignalObservation(
                lat=lat,
                lon=lon,
                kind="external_gap",
                aoi_id=aoi_id,
                aoi_label=aoi_label(aoi) if aoi else None,
            ))
    return {
        "detailRows": total,
        "outsideOfficialGraRows": outside,
        "mappedToPredictionAoiRows": mapped_to_aoi,
    }


def community_is_public(zone: Zone) -> bool:
    return (
        zone.community_total_raw >= MIN_COMMUNITY_REPORTS
        and len(zone.community_time_buckets) >= MIN_DISTINCT_SUBMISSION_MINUTES
    )


def priority_for(zone: Zone) -> tuple[str, int, list[str]]:
    safe_reports = zone.community_total_raw if community_is_public(zone) else 0
    structural = zone.community_events.get("structural_damage", 0) if safe_reports else 0
    official = zone.ems_official_destroyed_damaged
    monitor = zone.ems_monitor_destroyed_damaged
    external = zone.external_gap_candidates if zone.external_gap_candidates >= MIN_EXTERNAL_GAP_CANDIDATES else 0
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
    if monitor:
        score += min(20, max(2, monitor // 25))
        reasons.append(f"{monitor} MONIT01 destroyed/damaged points, kept separate from GRA")
    if external:
        score += min(30, max(8, external // 4))
        reasons.append(f"{external} external candidates outside GRA")
    if structural >= 5 and official == 0:
        score += 25
        reasons.append("gap: community structural reports without GRA damage in this zone")
    if external >= 50 and official == 0:
        score += 20
        reasons.append("gap: dense external candidates outside GRA")
    if score >= 70:
        return "high", score, reasons
    if score >= 35:
        return "medium", score, reasons
    return "low", score, reasons


def round_coordinates(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, int):
        return value
    if isinstance(value, tuple):
        return [round_coordinates(item) for item in value]
    if isinstance(value, list):
        return [round_coordinates(item) for item in value]
    if isinstance(value, dict):
        return {key: round_coordinates(item) for key, item in value.items()}
    return value


def public_geometry_for(zone: Zone) -> Any | None:
    return zone.public_geometry


def geojson_geometry(geometry: Any) -> dict[str, Any]:
    return round_coordinates(mapping(geometry))


def visible_properties(zone: Zone, sequence: int, aois: list[dict[str, Any]], geometry: Any) -> dict[str, Any] | None:
    safe_reports = community_is_public(zone)
    external_visible = zone.external_gap_candidates >= MIN_EXTERNAL_GAP_CANDIDATES
    ems_visible = (
        zone.ems_official_destroyed_damaged
        + zone.ems_official_possible
        + zone.ems_monitor_destroyed_damaged
        + zone.ems_monitor_possible
    ) > 0
    if not safe_reports and not external_visible and not ems_visible:
        return None
    if not zone.aoi_ids:
        add_aoi_hint(zone, aois, geometry)
    priority, score, reasons = priority_for(zone)
    community_events = {
        key: int(value)
        for key, value in zone.community_events.items()
        if safe_reports and value > 0
    }
    return {
        "id": f"ops-zone-{sequence:03d}",
        "sectorId": zone.sector_id,
        "sectorLabel": zone.sector_label,
        "sectorRow": zone.sector_row,
        "sectorCol": zone.sector_col,
        "priority": priority,
        "score": score,
        "communityReports": int(zone.community_total_raw) if safe_reports else None,
        "communityReportsSuppressed": not safe_reports and zone.community_total_raw > 0,
        "communityEvents": community_events,
        "latestSubmissionDate": zone.latest_submission[:10] if safe_reports and zone.latest_submission else None,
        "emsOfficialDestroyedDamaged": zone.ems_official_destroyed_damaged,
        "emsOfficialPossible": zone.ems_official_possible,
        "emsMonitorDestroyedDamaged": zone.ems_monitor_destroyed_damaged,
        "emsMonitorPossible": zone.ems_monitor_possible,
        "externalGapCandidates": zone.external_gap_candidates if external_visible else None,
        "externalGapSuppressed": not external_visible and zone.external_gap_candidates > 0,
        "aoiIds": sorted(zone.aoi_ids),
        "aoiLabels": sorted(zone.aoi_labels)[:3],
        "reasons": reasons[:4],
        "geometryMethod": zone.geometry_method,
        "geometrySource": zone.geometry_source,
        "overlapPolicy": IMPACT_OVERLAP_POLICY,
        "isOfficialDamageBoundary": False,
        "impactEnvelopeBufferDegrees": IMPACT_ENVELOPE_BUFFER_DEGREES,
        "publicNote": f"{zone.public_note} No names, phones, links, photos, text, exact report points, or addresses are published.",
    }


def build_geojson(observations: list[SignalObservation], aois: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    zones = build_impact_zones(aois)
    assignment_stats = assign_observations_to_sector_zones(observations, zones)
    ordered = sorted(
        zones,
        key=lambda zone: (
            {"high": 0, "medium": 1, "low": 2}[priority_for(zone)[0]],
            -priority_for(zone)[1],
            -zone.community_total_raw,
            -zone.external_gap_candidates,
        ),
    )
    features: list[dict[str, Any]] = []
    sequence = 1
    for zone in ordered:
        geometry = public_geometry_for(zone)
        if geometry is None:
            continue
        props = visible_properties(zone, sequence, aois, geometry)
        if not props:
            continue
        features.append({"type": "Feature", "properties": props, "geometry": geojson_geometry(geometry)})
        sequence += 1
    return {
        "type": "FeatureCollection",
        "metadata": {
            "status": "public-aggregate-not-official-damage",
            "generatedAt": generated_at,
            "geometryMethod": "evidence_impact_envelopes",
            "impactOverlapPolicy": IMPACT_OVERLAP_POLICY,
            "impactEnvelopeBufferDegrees": IMPACT_ENVELOPE_BUFFER_DEGREES,
            "impactEnvelopeInsetDegrees": IMPACT_ENVELOPE_INSET_DEGREES,
            "impactEnvelopeSimplifyDegrees": IMPACT_ENVELOPE_SIMPLIFY_DEGREES,
            "impactEnvelopeMinAreaDegrees": IMPACT_ENVELOPE_MIN_AREA_DEGREES,
            "sectorAssignment": assignment_stats,
            "minCommunityReports": MIN_COMMUNITY_REPORTS,
            "minDistinctSubmissionMinutes": MIN_DISTINCT_SUBMISSION_MINUTES,
            "minExternalGapCandidates": MIN_EXTERNAL_GAP_CANDIDATES,
            "warning": "Operational signals are triage guidance only. EMS remains the official source of damage counts.",
        },
        "features": features,
    }


def main() -> int:
    generated_at = now_utc()
    observations: list[SignalObservation] = []
    aois = load_catalog()
    kobo = add_kobo(observations)
    whatsapp = add_whatsapp(observations)
    ems = add_ems(observations, aois)
    external = add_external_gaps(observations, aois)
    geojson = build_geojson(observations, aois, generated_at)
    priority_counts = Counter(feature["properties"]["priority"] for feature in geojson["features"])
    summary = {
        "status": "public-aggregate-not-official-damage",
        "generatedAt": generated_at,
        "privacy": {
            "rawKoboWritten": False,
            "rawWhatsappWritten": False,
            "exactReportPointsWritten": False,
            "freeTextWritten": False,
            "minCommunityReportsPerVisibleZone": MIN_COMMUNITY_REPORTS,
            "minDistinctSubmissionMinutesPerVisibleZone": MIN_DISTINCT_SUBMISSION_MINUTES,
            "minCommunityReportsPerVisibleCell": MIN_COMMUNITY_REPORTS,
            "minDistinctSubmissionMinutesPerVisibleCell": MIN_DISTINCT_SUBMISSION_MINUTES,
            "geometryMethod": "evidence_impact_envelopes",
            "impactOverlapPolicy": IMPACT_OVERLAP_POLICY,
            "impactEnvelopeBufferDegrees": IMPACT_ENVELOPE_BUFFER_DEGREES,
            "impactEnvelopeInsetDegrees": IMPACT_ENVELOPE_INSET_DEGREES,
            "impactEnvelopeSimplifyDegrees": IMPACT_ENVELOPE_SIMPLIFY_DEGREES,
            "impactEnvelopeMinAreaDegrees": IMPACT_ENVELOPE_MIN_AREA_DEGREES,
        },
        "kobo": kobo,
        "whatsapp": whatsapp,
        "emsCounts": ems,
        "externalGap": external,
        "visibleZones": len(geojson["features"]),
        "visibleCells": len(geojson["features"]),
        "sectorAssignment": geojson["metadata"].get("sectorAssignment", {}),
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
