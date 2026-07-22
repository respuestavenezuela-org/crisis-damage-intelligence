"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import type { Language } from "@/components/types";
import styles from "./full-pilot-evidence.module.css";

type EvidenceImage = {
  role: "pre_comparator" | "post_detection";
  acquisitionUtc: string;
  sensor?: string;
  sourceFamily?: string;
  license?: string;
  nativeImage: string;
  nativeLocalFallback?: string | null;
  nativeSha256: string;
  enhancedImage?: string | null;
  enhancedLocalFallback?: string | null;
};

type EvidencePair = {
  pairId: string;
  targetDetection: { class: string; confidence: number };
  images: EvidenceImage[];
};

type Observation = {
  cellId: string;
  longitude: number;
  latitude: number;
  firstVisibleAcquisitionUtc?: string | null;
  hoursAfterEvent?: number | null;
  evidenceTier: string;
  consensus: string;
  priorityScore: number;
  assetCategories: string[];
  detector?: {
    sameAcquisitionCounts?: Record<string, number>;
    positiveMaxCountDeltas?: Record<string, number>;
  };
  evidencePair?: EvidencePair | null;
};

type PublicEvidenceSummary = {
  updatedAt: string;
  status: string;
  coverage: {
    gridCells: number;
    eligibleImageryStacks: number;
    pairedVlmCoverage: number;
    postEventOnlyCells: number;
    candidateCells: number;
    withinFirst72Hours: number;
    waldo30Cells: number;
    cropPairs: number;
    nativeCropImages: number;
    enhancedDisplayImages: number;
  };
  evidenceTierCounts: Record<string, number>;
  timelineEvents: Array<{
    acquisitionUtc: string;
    hoursAfterEvent: number;
    candidateCells: number;
    bothModelsPositive: number;
    detectorSupported: number;
  }>;
  topObservations: Observation[];
  documentaryEvidence: {
    conflictsAndBounds: Array<{
      topic: string;
      topicEs?: string;
      finding: string;
      findingEs?: string;
      interpretation: string;
      interpretationEs?: string;
    }>;
    sources: Array<{
      id: string;
      publisher: string;
      sourceType: string;
      publishedAt: string;
      url: string;
      places: string[];
      claims: string[];
      claimsEs?: string[];
      timePrecision: string;
      limitations: string;
    }>;
  };
  downloads: {
    candidateGeoJson: string;
    candidateJsonl: string;
    cropManifest: string;
  };
  guardrails: string[];
};

const content = {
  es: {
    kicker: "Piloto aéreo completo · triage automatizado",
    title: "2.283 celdas entre Catia La Mar, La Guaira y Caraballeda",
    intro:
      "Qwen y MiniMax comparan las mejores imágenes útiles por fecha en celdas de 250 m y recortes nativos de 768 × 768 px. WALDO30 aporta una segunda señal sobre objetos. Ningún resultado automatizado se publica como hecho oficial.",
    loading: "Cargando el paquete de evidencia ampliado…",
    unavailable:
      "El paquete ampliado todavía no está disponible. La cronología y la evidencia oficial siguen funcionando.",
    cells: "celdas del piloto",
    paired: "comparadas por ambos VLM",
    candidates: "candidatas de triage",
    first72: "con señal fechada ≤72 h",
    native: "recortes nativos",
    aiTriage: "AI triage · requiere revisar píxeles nativos",
    firstVisible: "Primera adquisición visible",
    hours: "horas después",
    pre: "Referencia anterior",
    post: "Detección posterior",
    enhanced: "Vista 2× solo visualización",
    detection: "Detección",
    confidence: "confianza",
    showMore: "Mostrar más evidencia",
    showLess: "Mostrar menos",
    chronology: "Límites temporales de la imagen",
    chronologyNote:
      "Una fecha significa “visible a más tardar en esta adquisición”; no es la hora real de llegada.",
    crossChecks: "Lo que aportan las fuentes de terreno",
    sources: "Fuentes documentales y afirmaciones acotadas",
    sourceLimit:
      "Cada enlace respalda las afirmaciones listadas; sus límites de tiempo y cobertura se conservan en el conjunto descargable.",
    downloads: "Descargar datos de triage",
    geojson: "GeoJSON de candidatas",
    jsonl: "Observaciones JSONL",
    crops: "Manifiesto de recortes",
    absence: "No observado no significa que no ocurrió.",
    counts: "Los conteos entre fechas nunca son un total simultáneo de activos.",
    detector: "Señal independiente del detector",
  },
  en: {
    kicker: "Full aerial pilot · automated triage",
    title: "2,283 cells across Catia La Mar, La Guaira and Caraballeda",
    intro:
      "Qwen and MiniMax compare the best usable image per date in 250 m cells using 768 × 768 px native crops. WALDO30 supplies a second object signal. No automated output is published as an official fact.",
    loading: "Loading the expanded evidence package…",
    unavailable:
      "The expanded package is not available yet. The chronology and official evidence remain usable.",
    cells: "pilot cells",
    paired: "compared by both VLMs",
    candidates: "triage candidates",
    first72: "with a dated signal ≤72 h",
    native: "native crops",
    aiTriage: "AI triage · native pixels require review",
    firstVisible: "First-visible acquisition",
    hours: "hours after",
    pre: "Earlier reference",
    post: "Post-event detection",
    enhanced: "2× display-only view",
    detection: "Detection",
    confidence: "confidence",
    showMore: "Show more evidence",
    showLess: "Show less",
    chronology: "Imagery time bounds",
    chronologyNote:
      "A date means “visible by this acquisition”; it is not the actual arrival time.",
    crossChecks: "What field sources add",
    sources: "Documentary sources and bounded claims",
    sourceLimit:
      "Each link supports the listed claims; its time and coverage limitations remain in the downloadable dataset.",
    downloads: "Download triage data",
    geojson: "Candidate GeoJSON",
    jsonl: "Observations JSONL",
    crops: "Crop manifest",
    absence: "Not observed does not mean it did not happen.",
    counts: "Counts across dates are never a simultaneous asset total.",
    detector: "Independent detector signal",
  },
};

function formatDate(value: string, language: Language) {
  return new Intl.DateTimeFormat(language === "es" ? "es-VE" : "en-US", {
    timeZone: "America/Caracas",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function formatNumber(value: number, language: Language) {
  return value.toLocaleString(language === "es" ? "es-VE" : "en-US");
}

function categoryLabel(value: string, language: Language) {
  const labels: Record<string, [string, string]> = {
    heavy_machinery: ["Maquinaria", "Machinery"],
    trucks_or_large_vehicles: ["Camiones", "Trucks"],
    temporary_shelter: ["Refugio temporal", "Temporary shelter"],
    collection_or_staging: ["Acopio o despliegue", "Collection or staging"],
    debris_clearance: ["Retiro de escombros", "Debris clearance"],
    emergency_or_service_vehicle: [
      "Vehículo de emergencia",
      "Emergency vehicle",
    ],
  };
  return labels[value]?.[language === "es" ? 0 : 1] ?? value;
}

function EvidenceChip({
  image,
  cellId,
  label,
  language,
}: {
  image: EvidenceImage;
  cellId: string;
  label: string;
  language: Language;
}) {
  const [source, setSource] = useState(image.nativeImage);
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div
        className={styles.imageUnavailable}
        role="img"
        aria-label={`${label} ${cellId}`}
      >
        {language === "es" ? "Imagen no disponible" : "Image unavailable"}
      </div>
    );
  }

  return (
    <Image
      src={source}
      alt={`${label} ${cellId}`}
      width={320}
      height={320}
      loading="lazy"
      unoptimized
      onError={() => {
        if (image.nativeLocalFallback && source !== image.nativeLocalFallback) {
          setSource(image.nativeLocalFallback);
        } else {
          setFailed(true);
        }
      }}
    />
  );
}

export default function FullPilotEvidencePanel({
  language,
}: {
  language: Language;
}) {
  const [data, setData] = useState<PublicEvidenceSummary | null>(null);
  const [error, setError] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const t = content[language];

  useEffect(() => {
    let cancelled = false;
    fetch("/data/reconstruction/full-pilot-response-evidence-summary.json")
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.json() as Promise<PublicEvidenceSummary>;
      })
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const observations = useMemo(
    () => data?.topObservations.slice(0, expanded ? 24 : 6) ?? [],
    [data, expanded],
  );

  if (!data) {
    return (
      <section className={styles.panel} aria-live="polite">
        <p className={styles.kicker}>{t.kicker}</p>
        <p>{error ? t.unavailable : t.loading}</p>
      </section>
    );
  }

  return (
    <section className={styles.panel} id="full-pilot-evidence">
      <header className={styles.header}>
        <div>
          <p className={styles.kicker}>{t.kicker}</p>
          <h2>{t.title}</h2>
        </div>
        <p>{t.intro}</p>
      </header>

      <div className={styles.stats}>
        <div>
          <b>{formatNumber(data.coverage.gridCells, language)}</b>
          <span>{t.cells}</span>
        </div>
        <div>
          <b>{formatNumber(data.coverage.pairedVlmCoverage, language)}</b>
          <span>{t.paired}</span>
        </div>
        <div>
          <b>{formatNumber(data.coverage.candidateCells, language)}</b>
          <span>{t.candidates}</span>
        </div>
        <div>
          <b>{formatNumber(data.coverage.withinFirst72Hours, language)}</b>
          <span>{t.first72}</span>
        </div>
        <div>
          <b>{formatNumber(data.coverage.nativeCropImages, language)}</b>
          <span>{t.native}</span>
        </div>
      </div>

      <aside className={styles.warning}>
        <b>{t.aiTriage}</b>
        <span>{t.absence}</span>
        <span>{t.counts}</span>
      </aside>

      <div className={styles.evidenceGrid}>
        {observations.map((observation) => {
          const images = observation.evidencePair?.images ?? [];
          const before = images.find(
            (image) => image.role === "pre_comparator",
          );
          const after = images.find((image) => image.role === "post_detection");
          return (
            <article key={observation.cellId} className={styles.card}>
              <div className={styles.cardHeading}>
                <div>
                  <span>{observation.evidenceTier.replaceAll("_", " ")}</span>
                  <h3>{observation.cellId}</h3>
                </div>
                <b>{observation.priorityScore}</b>
              </div>
              <div className={styles.categories}>
                {observation.assetCategories.map((category) => (
                  <span key={category}>
                    {categoryLabel(category, language)}
                  </span>
                ))}
              </div>
              {(before || after) && (
                <div className={styles.imagePair}>
                  {[before, after].filter(Boolean).map((image) => (
                    <figure key={`${observation.cellId}-${image!.role}`}>
                      <EvidenceChip
                        image={image!}
                        cellId={observation.cellId}
                        label={
                          image!.role === "pre_comparator" ? t.pre : t.post
                        }
                        language={language}
                      />
                      <figcaption>
                        <b>
                          {image!.role === "pre_comparator" ? t.pre : t.post}
                        </b>
                        <span>
                          {formatDate(image!.acquisitionUtc, language)}
                        </span>
                        <span>
                          {image!.sensor ?? image!.sourceFamily ?? "—"}
                          {image!.license ? ` · ${image!.license}` : ""}
                        </span>
                      </figcaption>
                    </figure>
                  ))}
                </div>
              )}
              <dl className={styles.metadata}>
                <div>
                  <dt>{t.firstVisible}</dt>
                  <dd>
                    {observation.firstVisibleAcquisitionUtc
                      ? formatDate(
                          observation.firstVisibleAcquisitionUtc,
                          language,
                        )
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt>{t.hours}</dt>
                  <dd>{observation.hoursAfterEvent ?? "—"}</dd>
                </div>
                {observation.evidencePair && (
                  <div>
                    <dt>{t.detection}</dt>
                    <dd>
                      {observation.evidencePair.targetDetection.class} ·{" "}
                      {Math.round(
                        observation.evidencePair.targetDetection.confidence *
                          100,
                      )}
                      % {t.confidence}
                    </dd>
                  </div>
                )}
              </dl>
              {after?.enhancedImage && (
                <a href={after.enhancedImage} target="_blank" rel="noreferrer">
                  {t.enhanced} ↗
                </a>
              )}
            </article>
          );
        })}
      </div>

      {data.topObservations.length > 6 && (
        <button
          className={styles.expand}
          type="button"
          onClick={() => setExpanded((value) => !value)}
        >
          {expanded ? t.showLess : t.showMore}
        </button>
      )}

      <div className={styles.lowerGrid}>
        <section>
          <h3>{t.chronology}</h3>
          <p>{t.chronologyNote}</p>
          <ol className={styles.timeline}>
            {data.timelineEvents.map((event) => (
              <li key={event.acquisitionUtc}>
                <time>{formatDate(event.acquisitionUtc, language)}</time>
                <b>+{event.hoursAfterEvent} h</b>
                <span>
                  {event.candidateCells} {t.candidates} ·{" "}
                  {event.bothModelsPositive} Qwen + MiniMax ·{" "}
                  {event.detectorSupported} {t.detector.toLocaleLowerCase()}
                </span>
              </li>
            ))}
          </ol>
        </section>
        <section>
          <h3>{t.crossChecks}</h3>
          <div className={styles.crossChecks}>
            {data.documentaryEvidence.conflictsAndBounds.map((item) => (
              <article key={item.topic}>
                <b>
                  {language === "es"
                    ? (item.topicEs ?? item.topic)
                    : item.topic}
                </b>
                <p>
                  {language === "es"
                    ? (item.findingEs ?? item.finding)
                    : item.finding}
                </p>
                <small>
                  {language === "es"
                    ? (item.interpretationEs ?? item.interpretation)
                    : item.interpretation}
                </small>
              </article>
            ))}
          </div>
        </section>
      </div>

      <section className={styles.sourceSection}>
        <h3>{t.sources}</h3>
        <p>{t.sourceLimit}</p>
        <div className={styles.sourceGrid}>
          {data.documentaryEvidence.sources.map((source) => (
            <details key={source.id}>
              <summary>
                <span>{source.publisher}</span>
                <time>{source.publishedAt.slice(0, 10)}</time>
              </summary>
              <p>{source.places.join(" · ")}</p>
              <ul>
                {(language === "es"
                  ? (source.claimsEs ?? source.claims)
                  : source.claims
                ).map((claim) => (
                  <li key={claim}>{claim}</li>
                ))}
              </ul>
              <a href={source.url} target="_blank" rel="noreferrer">
                {language === "es" ? "Abrir fuente" : "Open source"} ↗
              </a>
            </details>
          ))}
        </div>
      </section>

      <footer className={styles.downloads}>
        <b>{t.downloads}</b>
        <a href={data.downloads.candidateGeoJson}>{t.geojson}</a>
        <a href={data.downloads.candidateJsonl}>{t.jsonl}</a>
        <a href={data.downloads.cropManifest}>{t.crops}</a>
      </footer>
    </section>
  );
}
