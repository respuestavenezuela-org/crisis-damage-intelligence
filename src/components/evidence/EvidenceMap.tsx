"use client";

import type { EvidenceLanguage, EvidenceObservation } from "./types";
import styles from "./evidence-explorer.module.css";

const CITY_LABELS = [
  { name: "Catia La Mar", longitude: -67.0305, latitude: 10.5988 },
  { name: "La Guaira", longitude: -66.9312, latitude: 10.6048 },
  { name: "Caraballeda", longitude: -66.8527, latitude: 10.6136 },
];

const categoryColors: Record<string, string> = {
  heavy_machinery: "#e1a52a",
  trucks_or_large_vehicles: "#c85836",
  temporary_shelter: "#2e7b68",
  collection_or_staging: "#4769a8",
  debris_clearance: "#7c6655",
  emergency_or_service_vehicle: "#b84562",
};

function markerColor(observation: EvidenceObservation) {
  for (const category of Object.keys(categoryColors)) {
    if (observation.assetCategories.includes(category)) {
      return categoryColors[category];
    }
  }
  return "#656b64";
}

export default function EvidenceMap({
  observations,
  filtered,
  selectedCellId,
  onSelect,
  label,
  language,
}: {
  observations: EvidenceObservation[];
  filtered: EvidenceObservation[];
  selectedCellId: string | null;
  onSelect: (cellId: string) => void;
  label: string;
  language: EvidenceLanguage;
}) {
  const longitudeValues = observations.map((item) => item.longitude);
  const latitudeValues = observations.map((item) => item.latitude);
  const west = Math.min(...longitudeValues) - 0.005;
  const east = Math.max(...longitudeValues) + 0.005;
  const south = Math.min(...latitudeValues) - 0.004;
  const north = Math.max(...latitudeValues) + 0.004;
  const width = 1000;
  const height = 420;
  const padX = 28;
  const padY = 26;
  const x = (longitude: number) =>
    padX + ((longitude - west) / (east - west)) * (width - padX * 2);
  const y = (latitude: number) =>
    height - padY - ((latitude - south) / (north - south)) * (height - padY * 2);
  const filteredIds = new Set(filtered.map((item) => item.cellId));

  return (
    <div className={styles.mapFrame}>
      <div className={styles.mapHeading}>
        <div>
          <span>WGS84 · 250 m</span>
          <b>{label}</b>
        </div>
        <strong>{filtered.length}</strong>
      </div>
      <svg
        className={styles.map}
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={label}
      >
        <defs>
          <pattern id="evidence-grid" width="64" height="64" patternUnits="userSpaceOnUse">
            <path d="M 64 0 L 0 0 0 64" fill="none" stroke="currentColor" strokeWidth="0.7" />
          </pattern>
          <linearGradient id="evidence-sea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#dfe9e5" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#bad0ca" stopOpacity="0.9" />
          </linearGradient>
        </defs>
        <rect width={width} height={height} className={styles.mapPaper} />
        <rect width={width} height={height} fill="url(#evidence-grid)" className={styles.mapGrid} />
        <path
          d="M0,348 C130,328 210,359 335,336 C455,314 555,350 675,329 C792,307 880,338 1000,316 L1000,420 L0,420 Z"
          fill="url(#evidence-sea)"
          className={styles.sea}
        />
        <path
          d="M0,348 C130,328 210,359 335,336 C455,314 555,350 675,329 C792,307 880,338 1000,316"
          className={styles.coastline}
        />
        <text x="840" y="382" className={styles.seaLabel}>
          {language === "es" ? "MAR CARIBE" : "CARIBBEAN SEA"}
        </text>

        {observations.map((observation) => (
          <circle
            key={`base-${observation.cellId}`}
            cx={x(observation.longitude)}
            cy={y(observation.latitude)}
            r={filteredIds.has(observation.cellId) ? 2.8 : 1.7}
            className={filteredIds.has(observation.cellId) ? styles.basePointActive : styles.basePoint}
          />
        ))}

        {filtered.map((observation) => {
          const selected = observation.cellId === selectedCellId;
          return (
            <g
              key={observation.cellId}
              className={styles.mapTarget}
              onClick={() => onSelect(observation.cellId)}
            >
              <circle
                cx={x(observation.longitude)}
                cy={y(observation.latitude)}
                r="12"
                fill="transparent"
              />
              <circle
                cx={x(observation.longitude)}
                cy={y(observation.latitude)}
                r={selected ? 7 : 4}
                fill={markerColor(observation)}
                className={selected ? styles.selectedPoint : styles.resultPoint}
              />
            </g>
          );
        })}

        {CITY_LABELS.map((city) => (
          <g key={city.name} transform={`translate(${x(city.longitude)},${y(city.latitude)})`}>
            <line x1="0" y1="-18" x2="0" y2="-5" className={styles.cityLine} />
            <rect x="-54" y="-40" width="108" height="23" rx="2" className={styles.cityPlate} />
            <text x="0" y="-24" textAnchor="middle" className={styles.cityLabel}>{city.name}</text>
          </g>
        ))}
      </svg>
      <div className={styles.mapLegend} aria-hidden="true">
        <span>
          <i style={{ background: categoryColors.heavy_machinery }} />
          {language === "es" ? "Maquinaria" : "Machinery"}
        </span>
        <span>
          <i style={{ background: categoryColors.trucks_or_large_vehicles }} />
          {language === "es" ? "Vehículos" : "Vehicles"}
        </span>
        <span>
          <i style={{ background: categoryColors.temporary_shelter }} />
          {language === "es" ? "Refugio" : "Shelter"}
        </span>
        <span>
          <i style={{ background: categoryColors.collection_or_staging }} />
          {language === "es" ? "Acopio" : "Staging"}
        </span>
      </div>
    </div>
  );
}
