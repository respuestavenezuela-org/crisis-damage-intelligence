"use client";

import Image from "next/image";
import Link from "next/link";
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import {
  DEFAULT_LANGUAGE,
  persistLang,
  readStoredLang,
  subscribeStoredLang,
} from "@/lib/lang";
import EvidenceMap from "./EvidenceMap";
import type {
  CuratedEvidence,
  CuratedObservation,
  EvidenceCellDetail,
  EvidenceImage,
  EvidenceLanguage,
  EvidenceObservation,
  EvidenceSummary,
} from "./types";
import styles from "./evidence-explorer.module.css";

type ExplorerTab = "explorer" | "highlights" | "chronology" | "sources";
type SortMode = "strength" | "earliest" | "latest" | "cell";
type ImageMode = "native" | "enhanced";

const PAGE_SIZE = 24;
const SUMMARY_URL =
  "/data/reconstruction/full-pilot-evidence-explorer-summary.json";
const OBSERVATIONS_URL =
  "/data/reconstruction/full-pilot-response-evidence.jsonl";
const CURATED_URL =
  "/data/reconstruction/aerial-response-evidence-la-guaira.json";
const CELL_DETAIL_BASE =
  "/data/reconstruction/full-pilot-evidence-cells";

const copy = {
  es: {
    title: "Atlas de evidencia aérea",
    eyebrow: "La Guaira · Caraballeda · Catia La Mar",
    dek: "Todos los resultados del piloto, desde los diez casos revisados hasta las 399 celdas candidatas. Cada señal conserva sus fechas, modelos, imágenes y límites.",
    back: "Volver a la cronología",
    map: "Abrir mapa de daños",
    candidates: "celdas candidatas",
    pairs: "pares de evidencia",
    reviewed: "casos revisados",
    within72: "visibles ≤72 h",
    explorer: "Todas las candidatas",
    highlights: "10 revisadas",
    chronology: "Cronología",
    sources: "Fuentes",
    triage: "Triage automatizado",
    triageText:
      "Una candidata no es un hecho confirmado. Los resultados señalan dónde revisar píxeles; no prueban función, propiedad, suficiencia ni hora real de llegada.",
    loading: "Cargando el índice de evidencia…",
    error: "No se pudo cargar el índice. Los archivos descargables siguen disponibles.",
    search: "Buscar celda o coordenada",
    searchPlaceholder: "pilot_r040_c046 o -66.85",
    category: "Observación",
    agreement: "Evidencia",
    time: "Ventana",
    imagery: "Imagen",
    all: "Todo",
    machinery: "Maquinaria",
    trucks: "Camiones",
    shelter: "Refugio temporal",
    staging: "Acopio",
    debris: "Escombros",
    emergency: "Emergencia",
    bothPositive: "Ambos VLM positivos",
    contested: "Contestado",
    detector: "Con señal WALDO30",
    beforeAfter: "Antes/después",
    postOnly: "Solo posterior",
    sort: "Ordenar",
    strongest: "Mayor señal",
    earliest: "Primera visible",
    latest: "Más tardía",
    cell: "ID de celda",
    results: "resultados",
    mapLabel: "Distribución geográfica de candidatas filtradas",
    selectPrompt: "Selecciona una celda",
    selectPromptText:
      "Abre una observación desde el mapa o la lista para inspeccionar sus pares de evidencia.",
    close: "Cerrar detalle",
    closeBackdrop: "Cerrar al tocar fuera del detalle",
    firstVisible: "Primera visible",
    afterEvent: "después del evento",
    models: "Lectura de modelos",
    detectorSignal: "Señal independiente WALDO30",
    noDetector: "Sin aumento positivo del detector",
    openLocation: "Abrir coordenadas",
    imageView: "Vista de imagen",
    native: "Píxeles nativos",
    enhanced: "Mejora 2×",
    displayOnly: "solo visualización",
    earlier: "Referencia anterior",
    later: "Detección posterior",
    pair: "Par",
    detection: "Detección candidata",
    confidence: "confianza",
    provenance: "Procedencia",
    source: "Fuente",
    license: "Licencia",
    noPair: "Esta candidata no tiene un recorte publicado.",
    page: "Página",
    previous: "Anterior",
    next: "Siguiente",
    showing: "Mostrando",
    reviewedIntro:
      "Estos diez casos fueron seleccionados después de revisión humana de píxeles nativos. Son ejemplos defendibles, no el universo completo de candidatas.",
    probable: "Probable respuesta",
    unresolved: "No resuelto",
    timelineIntro:
      "Cada barra indica cuántas celdas mostraron su primera señal visible en una adquisición. No representa la hora real de llegada.",
    filterThisWindow: "Ver candidatas de esta ventana",
    candidateCells: "celdas",
    bothModels: "ambos positivos",
    detectorSupported: "con detector",
    sourceIntro:
      "Las fuentes de terreno acotan lo que la imagen puede y no puede establecer.",
    openSource: "Abrir fuente",
    boundedFinding: "Conclusión acotada",
    downloads: "Descargar conjunto completo",
    geojson: "GeoJSON · 399 celdas",
    observations: "JSONL · observaciones",
    cropManifest: "JSONL · 500 pares",
    clear: "Limpiar filtros",
    noResults: "Ninguna candidata coincide con estos filtros.",
  },
  en: {
    title: "Aerial evidence atlas",
    eyebrow: "La Guaira · Caraballeda · Catia La Mar",
    dek: "Every pilot result, from ten reviewed cases to all 399 candidate cells. Each signal retains its dates, model outputs, imagery and limits.",
    back: "Back to the timeline",
    map: "Open damage map",
    candidates: "candidate cells",
    pairs: "evidence pairs",
    reviewed: "reviewed cases",
    within72: "visible ≤72 h",
    explorer: "All candidates",
    highlights: "10 reviewed",
    chronology: "Chronology",
    sources: "Sources",
    triage: "Automated triage",
    triageText:
      "A candidate is not a confirmed fact. Results identify pixels to review; they do not prove function, ownership, adequacy or actual arrival time.",
    loading: "Loading the evidence index…",
    error: "The evidence index could not load. Downloadable files remain available.",
    search: "Search cell or coordinate",
    searchPlaceholder: "pilot_r040_c046 or -66.85",
    category: "Observation",
    agreement: "Evidence",
    time: "Window",
    imagery: "Imagery",
    all: "All",
    machinery: "Machinery",
    trucks: "Trucks",
    shelter: "Temporary shelter",
    staging: "Staging",
    debris: "Debris",
    emergency: "Emergency",
    bothPositive: "Both VLMs positive",
    contested: "Contested",
    detector: "WALDO30 signal",
    beforeAfter: "Before/after",
    postOnly: "Post-event only",
    sort: "Sort",
    strongest: "Strongest signal",
    earliest: "First visible",
    latest: "Latest",
    cell: "Cell ID",
    results: "results",
    mapLabel: "Geographic distribution of filtered candidates",
    selectPrompt: "Select a cell",
    selectPromptText:
      "Open an observation from the map or list to inspect its evidence pairs.",
    close: "Close detail",
    closeBackdrop: "Close outside evidence detail",
    firstVisible: "First visible",
    afterEvent: "after the event",
    models: "Model reading",
    detectorSignal: "Independent WALDO30 signal",
    noDetector: "No positive detector increase",
    openLocation: "Open coordinates",
    imageView: "Image view",
    native: "Native pixels",
    enhanced: "2× enhancement",
    displayOnly: "display only",
    earlier: "Earlier reference",
    later: "Post-event detection",
    pair: "Pair",
    detection: "Candidate detection",
    confidence: "confidence",
    provenance: "Provenance",
    source: "Source",
    license: "License",
    noPair: "This candidate has no published crop.",
    page: "Page",
    previous: "Previous",
    next: "Next",
    showing: "Showing",
    reviewedIntro:
      "These ten cases were selected after human review of native pixels. They are defensible examples, not the complete candidate inventory.",
    probable: "Likely response",
    unresolved: "Unresolved",
    timelineIntro:
      "Each bar shows how many cells first became visible in an acquisition. It is not the actual arrival time.",
    filterThisWindow: "View candidates in this window",
    candidateCells: "cells",
    bothModels: "both positive",
    detectorSupported: "detector-supported",
    sourceIntro:
      "Field sources bound what imagery can and cannot establish.",
    openSource: "Open source",
    boundedFinding: "Bounded finding",
    downloads: "Download complete dataset",
    geojson: "GeoJSON · 399 cells",
    observations: "JSONL · observations",
    cropManifest: "JSONL · 500 pairs",
    clear: "Clear filters",
    noResults: "No candidates match these filters.",
  },
} satisfies Record<EvidenceLanguage, Record<string, string>>;

const categoryOptions = [
  ["all", "all"],
  ["heavy_machinery", "machinery"],
  ["trucks_or_large_vehicles", "trucks"],
  ["temporary_shelter", "shelter"],
  ["collection_or_staging", "staging"],
  ["debris_clearance", "debris"],
  ["emergency_or_service_vehicle", "emergency"],
] as const;

const timeOptions = [
  ["all", "all"],
  ["0_24h", "0–24 h"],
  ["24_48h", "24–48 h"],
  ["48_72h", "48–72 h"],
  ["72h_7d", "72 h–7 d"],
  ["after_7d", ">7 d"],
] as const;

const tierRank: Record<string, number> = {
  cross_model_positive_with_detector_delta: 4,
  cross_model_positive: 3,
  contested_positive_with_detector_delta: 2,
  contested_positive: 1,
};

function parseJsonl<T>(value: string): T[] {
  return value
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line) as T);
}

function formatNumber(value: number, language: EvidenceLanguage) {
  return value.toLocaleString(language === "es" ? "es-VE" : "en-US");
}

function formatAcquisition(value: string | null | undefined, language: EvidenceLanguage) {
  if (!value) return "—";
  const locale = language === "es" ? "es-VE" : "en-US";
  const instant = new Date(value);
  if (Number.isNaN(instant.getTime())) {
    const dates = value.split("/");
    if (dates.every((date) => /^\d{4}-\d{2}-\d{2}$/.test(date))) {
      const formatter = new Intl.DateTimeFormat(locale, {
        timeZone: "UTC",
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
      return dates
        .map((date) => formatter.format(new Date(`${date}T00:00:00Z`)))
        .join(" / ");
    }
    return value;
  }
  return new Intl.DateTimeFormat(locale, {
    timeZone: "America/Caracas",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(instant);
}

function categoryLabel(value: string, language: EvidenceLanguage) {
  const labels: Record<string, [string, string]> = {
    heavy_machinery: ["Maquinaria", "Machinery"],
    trucks_or_large_vehicles: ["Camiones", "Trucks"],
    temporary_shelter: ["Refugio temporal", "Temporary shelter"],
    collection_or_staging: ["Acopio", "Staging"],
    debris_clearance: ["Escombros", "Debris"],
    emergency_or_service_vehicle: ["Emergencia", "Emergency"],
  };
  return labels[value]?.[language === "es" ? 0 : 1] ?? value;
}

function tierLabel(value: string, language: EvidenceLanguage) {
  const labels: Record<string, [string, string]> = {
    cross_model_positive_with_detector_delta: [
      "Ambos VLM + detector",
      "Both VLMs + detector",
    ],
    cross_model_positive: ["Ambos VLM positivos", "Both VLMs positive"],
    contested_positive_with_detector_delta: [
      "Contestado + detector",
      "Contested + detector",
    ],
    contested_positive: ["Positivo contestado", "Contested positive"],
  };
  return labels[value]?.[language === "es" ? 0 : 1] ?? value;
}

function EvidenceImageView({
  image,
  mode,
  language,
}: {
  image: EvidenceImage;
  mode: ImageMode;
  language: EvidenceLanguage;
}) {
  const enhanced = mode === "enhanced" && image.enhancedImage;
  const preferred = enhanced ? image.enhancedImage! : image.nativeImage;
  const fallback = enhanced
    ? image.enhancedLocalFallback
    : image.nativeLocalFallback;
  const [source, setSource] = useState(preferred);
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className={styles.imageFailure} role="img">
        {language === "es" ? "Imagen no disponible" : "Image unavailable"}
      </div>
    );
  }

  return (
    <Image
      src={source}
      alt={`${image.role === "pre_comparator" ? copy[language].earlier : copy[language].later} · ${image.sceneId}`}
      width={768}
      height={768}
      sizes="(max-width: 760px) 92vw, 420px"
      loading="lazy"
      unoptimized
      onError={() => {
        if (fallback && source !== fallback) setSource(fallback);
        else setFailed(true);
      }}
    />
  );
}

function DetailPanel({
  detail,
  loading,
  error,
  language,
  onClose,
}: {
  detail: EvidenceCellDetail | null;
  loading: boolean;
  error: boolean;
  language: EvidenceLanguage;
  onClose: () => void;
}) {
  const t = copy[language];
  const [mode, setMode] = useState<ImageMode>("native");

  if (loading) {
    return (
      <aside className={styles.detailPanel} aria-live="polite">
        <button className={styles.closeDetail} type="button" onClick={onClose} aria-label={t.close}>×</button>
        <div className={styles.detailLoading}>{t.loading}</div>
      </aside>
    );
  }
  if (error || !detail) {
    return (
      <aside className={styles.detailPanel}>
        <button className={styles.closeDetail} type="button" onClick={onClose} aria-label={t.close}>×</button>
        <div className={styles.emptyDetail}>
          <span>399 / 500</span>
          <h2>{t.selectPrompt}</h2>
          <p>{error ? t.error : t.selectPromptText}</p>
        </div>
      </aside>
    );
  }

  const observation = detail.observation;
  const detectorCounts = observation.detector?.positiveMaxCountDeltas ?? {};

  return (
    <aside className={styles.detailPanel} aria-labelledby="selected-cell-title">
      <button className={styles.closeDetail} type="button" onClick={onClose} aria-label={t.close}>×</button>
      <div className={styles.detailTopline}>
        <span>{tierLabel(observation.evidenceTier, language)}</span>
        <b>{observation.priorityScore}</b>
      </div>
      <h2 id="selected-cell-title">{observation.cellId}</h2>
      <div className={styles.detailCategories}>
        {observation.assetCategories.map((category) => (
          <span key={category}>{categoryLabel(category, language)}</span>
        ))}
      </div>
      <dl className={styles.detailFacts}>
        <div>
          <dt>{t.firstVisible}</dt>
          <dd>{formatAcquisition(observation.firstVisibleAcquisitionUtc, language)}</dd>
        </div>
        <div>
          <dt>{t.afterEvent}</dt>
          <dd>{observation.hoursAfterEvent != null ? `${observation.hoursAfterEvent.toFixed(1)} h` : "—"}</dd>
        </div>
        <div>
          <dt>{t.models}</dt>
          <dd>{observation.consensus.replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>{t.imagery}</dt>
          <dd>{observation.stackStatus === "before_after" ? t.beforeAfter : t.postOnly}</dd>
        </div>
      </dl>
      <div className={styles.detectorBox}>
        <span>{t.detectorSignal}</span>
        {Object.keys(detectorCounts).length ? (
          <div>
            {Object.entries(detectorCounts).map(([name, value]) => (
              <b key={name}>{name} +{value}</b>
            ))}
          </div>
        ) : (
          <p>{t.noDetector}</p>
        )}
      </div>
      <a
        className={styles.locationLink}
        href={`https://www.google.com/maps/search/?api=1&query=${observation.latitude},${observation.longitude}`}
        target="_blank"
        rel="noreferrer"
      >
        {t.openLocation} ↗
      </a>

      <div className={styles.imageMode}>
        <span>{t.imageView}</span>
        <div>
          <button type="button" aria-pressed={mode === "native"} onClick={() => setMode("native")}>{t.native}</button>
          <button type="button" aria-pressed={mode === "enhanced"} onClick={() => setMode("enhanced")}>{t.enhanced}</button>
        </div>
      </div>
      {mode === "enhanced" && (
        <p className={styles.enhancedWarning}>AI / 2× · {t.displayOnly}</p>
      )}

      {detail.evidencePairs.length ? (
        <div className={styles.pairList}>
          {detail.evidencePairs.map((pair, pairIndex) => (
            <article key={pair.pairId} className={styles.pair}>
              <header>
                <span>{t.pair} {pairIndex + 1}/{detail.evidencePairs.length}</span>
                <b>{pair.targetDetection?.class ?? pair.pairId}</b>
                {pair.targetDetection?.confidence != null && (
                  <small>{Math.round(pair.targetDetection.confidence * 100)}% {t.confidence}</small>
                )}
              </header>
              <div className={styles.imagePair}>
                {pair.images.map((image) => (
                  <figure key={`${pair.pairId}-${image.role}`}>
                  <EvidenceImageView
                    key={`${pair.pairId}-${image.role}-${mode}`}
                    image={image}
                    mode={mode}
                    language={language}
                  />
                    <figcaption>
                      <b>{image.role === "pre_comparator" ? t.earlier : t.later}</b>
                      <span>{formatAcquisition(image.acquisitionUtc, language)}</span>
                      <small>{image.sensor ?? image.sceneId}</small>
                    </figcaption>
                  </figure>
                ))}
              </div>
              <details className={styles.provenance}>
                <summary>{t.provenance}</summary>
                {pair.images.map((image) => (
                  <div key={`${pair.pairId}-${image.role}-source`}>
                    <span>{t.source}: {image.sourceFamily ?? image.sceneId}</span>
                    <span>{t.license}: {image.license ?? "—"}</span>
                    <code>{image.nativeSha256.slice(0, 20)}…</code>
                  </div>
                ))}
              </details>
            </article>
          ))}
        </div>
      ) : (
        <p className={styles.noPair}>{t.noPair}</p>
      )}

      <div className={styles.detailPolicy}>
        <p>{detail.policy.nativePixels}</p>
        <p>{detail.policy.arrival}</p>
        <p>{detail.policy.absence}</p>
      </div>
    </aside>
  );
}

function HighlightCard({
  observation,
  language,
}: {
  observation: CuratedObservation;
  language: EvidenceLanguage;
}) {
  const t = copy[language];
  return (
    <article className={styles.highlightCard}>
      <figure>
        <Image
          src={observation.nativeImage}
          alt={observation.title[language]}
          width={768}
          height={768}
          sizes="(max-width: 760px) 94vw, 420px"
          loading="lazy"
          unoptimized
        />
        <figcaption>{observation.chipId} · {t.native}</figcaption>
      </figure>
      <div>
        <span>{observation.status === "likely-response-related" ? t.probable : t.unresolved}</span>
        <h3>{observation.title[language]}</h3>
        <p>{observation.finding[language]}</p>
        <small>{observation.location.label}</small>
        <a href={observation.mapUrl} target="_blank" rel="noreferrer">{t.openLocation} ↗</a>
      </div>
    </article>
  );
}

export default function EvidenceExplorer() {
  const language = useSyncExternalStore(
    subscribeStoredLang,
    readStoredLang,
    () => DEFAULT_LANGUAGE,
  );
  const t = copy[language];
  const [summary, setSummary] = useState<EvidenceSummary | null>(null);
  const [observations, setObservations] = useState<EvidenceObservation[]>([]);
  const [curated, setCurated] = useState<CuratedEvidence | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [tab, setTab] = useState<ExplorerTab>("explorer");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [agreement, setAgreement] = useState("all");
  const [timeWindow, setTimeWindow] = useState("all");
  const [imagery, setImagery] = useState("all");
  const [sort, setSort] = useState<SortMode>("strength");
  const [page, setPage] = useState(1);
  const [selectedCellId, setSelectedCellId] = useState<string | null>(null);
  const [detail, setDetail] = useState<EvidenceCellDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(false);
  const resultHeadingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch(SUMMARY_URL, { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error(`summary:${response.status}`);
        return response.json() as Promise<EvidenceSummary>;
      }),
      fetch(OBSERVATIONS_URL, { signal: controller.signal }).then(async (response) => {
        if (!response.ok) throw new Error(`observations:${response.status}`);
        return parseJsonl<EvidenceObservation>(await response.text());
      }),
    ])
      .then(([nextSummary, nextObservations]) => {
        setSummary(nextSummary);
        setObservations(nextObservations);
        const initialCell = new URLSearchParams(window.location.search).get("cell");
        if (initialCell && nextObservations.some((row) => row.cellId === initialCell)) {
          setDetailLoading(true);
          setDetailError(false);
          setDetail(null);
          setSelectedCellId(initialCell);
        }
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setLoadError(true);
        }
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (tab !== "highlights" || curated) return;
    const controller = new AbortController();
    fetch(CURATED_URL, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.json() as Promise<CuratedEvidence>;
      })
      .then(setCurated)
      .catch(() => undefined);
    return () => controller.abort();
  }, [tab, curated]);

  useEffect(() => {
    if (!selectedCellId) return;
    const controller = new AbortController();
    fetch(`${CELL_DETAIL_BASE}/${selectedCellId}.json`, {
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) throw new Error(String(response.status));
        return response.json() as Promise<EvidenceCellDetail>;
      })
      .then(setDetail)
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setDetailError(true);
        }
      })
      .finally(() => setDetailLoading(false));
    const url = new URL(window.location.href);
    url.searchParams.set("cell", selectedCellId);
    window.history.replaceState({}, "", url);
    return () => controller.abort();
  }, [selectedCellId]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const matches = observations.filter((observation) => {
      if (
        normalizedQuery &&
        ![
          observation.cellId,
          observation.longitude.toFixed(6),
          observation.latitude.toFixed(6),
        ].some((value) => value.toLowerCase().includes(normalizedQuery))
      ) return false;
      if (category !== "all" && !observation.assetCategories.includes(category)) return false;
      if (agreement === "both" && observation.consensus !== "both_positive") return false;
      if (agreement === "contested" && observation.consensus === "both_positive") return false;
      if (
        agreement === "detector" &&
        Object.keys(observation.detector?.positiveMaxCountDeltas ?? {}).length === 0
      ) return false;
      if (timeWindow !== "all" && observation.timeWindow !== timeWindow) return false;
      if (imagery !== "all" && observation.stackStatus !== imagery) return false;
      return true;
    });
    return matches.sort((a, b) => {
      if (sort === "earliest") {
        return (a.hoursAfterEvent ?? Number.MAX_VALUE) - (b.hoursAfterEvent ?? Number.MAX_VALUE);
      }
      if (sort === "latest") {
        return (b.hoursAfterEvent ?? -1) - (a.hoursAfterEvent ?? -1);
      }
      if (sort === "cell") return a.cellId.localeCompare(b.cellId);
      return (
        (tierRank[b.evidenceTier] ?? 0) - (tierRank[a.evidenceTier] ?? 0) ||
        b.priorityScore - a.priorityScore ||
        a.cellId.localeCompare(b.cellId)
      );
    });
  }, [observations, query, category, agreement, timeWindow, imagery, sort]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const paged = filtered.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE,
  );

  const selectCell = (cellId: string) => {
    setDetailLoading(true);
    setDetailError(false);
    setDetail(null);
    setSelectedCellId(cellId);
  };

  const closeDetail = () => {
    setSelectedCellId(null);
    setDetail(null);
    const url = new URL(window.location.href);
    url.searchParams.delete("cell");
    window.history.replaceState({}, "", url);
  };

  const changeLanguage = (nextLanguage: EvidenceLanguage) => {
    persistLang(nextLanguage);
    document.documentElement.lang = nextLanguage;
  };

  const clearFilters = () => {
    setQuery("");
    setCategory("all");
    setAgreement("all");
    setTimeWindow("all");
    setImagery("all");
    setPage(1);
  };

  const openTimeWindow = (window: string) => {
    setTimeWindow(window);
    setPage(1);
    setTab("explorer");
    requestAnimationFrame(() => resultHeadingRef.current?.focus());
  };

  return (
    <main className={styles.page}>
      <nav className={styles.topbar} aria-label={language === "es" ? "Navegación principal" : "Main navigation"}>
        <Link href="/" className={styles.wordmark}>
          <span>RV</span>
          <b>Respuesta Venezuela</b>
        </Link>
        <div className={styles.topActions}>
          <Link href="/timeline">{t.back}</Link>
          <div className={styles.languageSwitch} aria-label="Language">
            <button type="button" onClick={() => changeLanguage("es")} aria-pressed={language === "es"}>ES</button>
            <button type="button" onClick={() => changeLanguage("en")} aria-pressed={language === "en"}>EN</button>
          </div>
          <Link href="/" className={styles.mapLink}>{t.map}</Link>
        </div>
      </nav>

      <header className={styles.hero}>
        <div className={styles.heroIndex} aria-hidden="true">399</div>
        <div className={styles.heroCopy}>
          <p>{t.eyebrow}</p>
          <h1>{t.title}</h1>
          <span>{t.dek}</span>
        </div>
        <dl className={styles.heroStats}>
          <div><dt>399</dt><dd>{t.candidates}</dd></div>
          <div><dt>500</dt><dd>{t.pairs}</dd></div>
          <div><dt>10</dt><dd>{t.reviewed}</dd></div>
          <div><dt>311</dt><dd>{t.within72}</dd></div>
        </dl>
      </header>

      <aside className={styles.triageWarning}>
        <b>{t.triage}</b>
        <p>{t.triageText}</p>
        <span>Qwen · MiniMax · WALDO30</span>
      </aside>

      <div className={styles.tabRail} role="tablist" aria-label={t.title}>
        {([
          ["explorer", t.explorer, "399"],
          ["highlights", t.highlights, "10"],
          ["chronology", t.chronology, "14"],
          ["sources", t.sources, "8"],
        ] as const).map(([value, label, count]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            onClick={() => setTab(value)}
          >
            <span>{count}</span>{label}
          </button>
        ))}
      </div>

      {tab === "explorer" && (
        <section className={styles.explorer} aria-labelledby="all-candidates-title">
          <div className={styles.filters}>
            <label className={styles.searchField}>
              <span>{t.search}</span>
              <input
                type="search"
                value={query}
                placeholder={t.searchPlaceholder}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            <fieldset>
              <legend>{t.category}</legend>
              <div>
                {categoryOptions.map(([value, label]) => (
                  <button key={value} type="button" aria-pressed={category === value} onClick={() => setCategory(value)}>
                    {label === "all" ? t.all : t[label]}
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>{t.agreement}</legend>
              <div>
                <button type="button" aria-pressed={agreement === "all"} onClick={() => setAgreement("all")}>{t.all}</button>
                <button type="button" aria-pressed={agreement === "both"} onClick={() => setAgreement("both")}>{t.bothPositive}</button>
                <button type="button" aria-pressed={agreement === "contested"} onClick={() => setAgreement("contested")}>{t.contested}</button>
                <button type="button" aria-pressed={agreement === "detector"} onClick={() => setAgreement("detector")}>{t.detector}</button>
              </div>
            </fieldset>
            <fieldset>
              <legend>{t.time}</legend>
              <div>
                {timeOptions.map(([value, label]) => (
                  <button key={value} type="button" aria-pressed={timeWindow === value} onClick={() => setTimeWindow(value)}>
                    {label === "all" ? t.all : label}
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>{t.imagery}</legend>
              <div>
                <button type="button" aria-pressed={imagery === "all"} onClick={() => setImagery("all")}>{t.all}</button>
                <button type="button" aria-pressed={imagery === "before_after"} onClick={() => setImagery("before_after")}>{t.beforeAfter}</button>
                <button type="button" aria-pressed={imagery === "post_event_only"} onClick={() => setImagery("post_event_only")}>{t.postOnly}</button>
              </div>
            </fieldset>
          </div>

          {loading && <p className={styles.status} aria-live="polite">{t.loading}</p>}
          {loadError && <p className={`${styles.status} ${styles.error}`} role="alert">{t.error}</p>}

          {!loading && observations.length > 0 && (
            <>
              <div className={styles.resultBar}>
                <h2 id="all-candidates-title" ref={resultHeadingRef} tabIndex={-1}>
                  {formatNumber(filtered.length, language)} {t.results}
                </h2>
                <label>
                  <span>{t.sort}</span>
                  <select value={sort} onChange={(event) => setSort(event.target.value as SortMode)}>
                    <option value="strength">{t.strongest}</option>
                    <option value="earliest">{t.earliest}</option>
                    <option value="latest">{t.latest}</option>
                    <option value="cell">{t.cell}</option>
                  </select>
                </label>
                <button type="button" onClick={clearFilters}>{t.clear}</button>
              </div>

              <div className={styles.workspace}>
                <div className={styles.mapAndList}>
                  <EvidenceMap
                    observations={observations}
                    filtered={filtered}
                    selectedCellId={selectedCellId}
                    onSelect={selectCell}
                    label={t.mapLabel}
                    language={language}
                  />
                  {filtered.length ? (
                    <div className={styles.resultList}>
                      {paged.map((observation, index) => (
                        <button
                          key={observation.cellId}
                          type="button"
                          className={`${styles.resultCard} ${selectedCellId === observation.cellId ? styles.resultCardActive : ""}`}
                          onClick={() => selectCell(observation.cellId)}
                        >
                          <span className={styles.resultRank}>
                            {String((safePage - 1) * PAGE_SIZE + index + 1).padStart(3, "0")}
                          </span>
                          <div>
                            <small>{tierLabel(observation.evidenceTier, language)}</small>
                            <b>{observation.cellId}</b>
                            <p>
                              {observation.assetCategories
                                .slice(0, 3)
                                .map((item) => categoryLabel(item, language))
                                .join(" · ")}
                            </p>
                            <span>
                              {observation.hoursAfterEvent != null ? `+${observation.hoursAfterEvent.toFixed(1)} h` : "—"}
                              {" · "}
                              {observation.cropPairIds.length} {t.pairs}
                            </span>
                          </div>
                          <strong>{observation.priorityScore}</strong>
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className={styles.noResults}>{t.noResults}</p>
                  )}
                  <nav className={styles.pagination} aria-label={t.page}>
                    <button type="button" disabled={safePage === 1} onClick={() => setPage(Math.max(1, safePage - 1))}>{t.previous}</button>
                    <span>{t.page} {safePage}/{totalPages} · {t.showing} {paged.length}</span>
                    <button type="button" disabled={safePage === totalPages} onClick={() => setPage(Math.min(totalPages, safePage + 1))}>{t.next}</button>
                  </nav>
                </div>

                {selectedCellId && (
                  <button
                    type="button"
                    className={styles.detailBackdrop}
                    onClick={closeDetail}
                    aria-label={t.closeBackdrop}
                    tabIndex={-1}
                  />
                )}
                <DetailPanel
                  detail={detail}
                  loading={detailLoading}
                  error={detailError}
                  language={language}
                  onClose={closeDetail}
                />
              </div>
            </>
          )}
        </section>
      )}

      {tab === "highlights" && (
        <section className={styles.editorialSection} aria-labelledby="reviewed-title">
          <header>
            <span>10 / 399</span>
            <h2 id="reviewed-title">{t.highlights}</h2>
            <p>{t.reviewedIntro}</p>
          </header>
          {!curated ? (
            <p className={styles.status}>{t.loading}</p>
          ) : (
            <div className={styles.highlightGrid}>
              {curated.observations.map((observation) => (
                <HighlightCard key={observation.id} observation={observation} language={language} />
              ))}
            </div>
          )}
        </section>
      )}

      {tab === "chronology" && summary && (
        <section className={styles.editorialSection} aria-labelledby="chronology-title">
          <header>
            <span>14 {language === "es" ? "adquisiciones" : "acquisitions"}</span>
            <h2 id="chronology-title">{t.chronology}</h2>
            <p>{t.timelineIntro}</p>
          </header>
          <div className={styles.chronology}>
            {summary.timelineEvents.map((event, index) => {
              const max = Math.max(...summary.timelineEvents.map((item) => item.candidateCells));
              return (
                <article key={`${event.acquisitionUtc}-${index}`}>
                  <time>{formatAcquisition(event.acquisitionUtc, language)}</time>
                  <div>
                    <span style={{ width: `${Math.max(2, (event.candidateCells / max) * 100)}%` }} />
                  </div>
                  <dl>
                    <div><dt>{t.candidateCells}</dt><dd>{event.candidateCells}</dd></div>
                    <div><dt>{t.bothModels}</dt><dd>{event.bothModelsPositive}</dd></div>
                    <div><dt>{t.detectorSupported}</dt><dd>{event.detectorSupported}</dd></div>
                  </dl>
                  <button type="button" onClick={() => openTimeWindow(event.timeWindow)}>{t.filterThisWindow} →</button>
                </article>
              );
            })}
          </div>
        </section>
      )}

      {tab === "sources" && summary && (
        <section className={styles.editorialSection} aria-labelledby="sources-title">
          <header>
            <span>{summary.documentaryEvidence.sources.length} {t.sources.toLowerCase()}</span>
            <h2 id="sources-title">{t.sources}</h2>
            <p>{t.sourceIntro}</p>
          </header>
          <div className={styles.sourceBounds}>
            {summary.documentaryEvidence.conflictsAndBounds.map((bound) => (
              <article key={bound.topic}>
                <span>{t.boundedFinding}</span>
                <h3>{language === "es" ? bound.topicEs ?? bound.topic : bound.topic}</h3>
                <p>{language === "es" ? bound.findingEs ?? bound.finding : bound.finding}</p>
                <small>{language === "es" ? bound.interpretationEs ?? bound.interpretation : bound.interpretation}</small>
              </article>
            ))}
          </div>
          <div className={styles.sources}>
            {summary.documentaryEvidence.sources.map((source, index) => (
              <article key={source.id}>
                <span>{String(index + 1).padStart(2, "0")} · {source.sourceType}</span>
                <h3>{source.publisher}</h3>
                <time>{source.publishedAt.slice(0, 10)}</time>
                <ul>
                  {(language === "es" ? source.claimsEs ?? source.claims : source.claims).map((claim) => (
                    <li key={claim}>{claim}</li>
                  ))}
                </ul>
                <p>{source.limitations}</p>
                <a href={source.url} target="_blank" rel="noreferrer">{t.openSource} ↗</a>
              </article>
            ))}
          </div>
        </section>
      )}

      <footer className={styles.footer}>
        <div>
          <b>{t.downloads}</b>
          <p>{summary?.method.arrivalRule ?? t.triageText}</p>
        </div>
        <nav aria-label={t.downloads}>
          <a href={summary?.downloads.candidateGeoJson ?? "/data/reconstruction/full-pilot-response-evidence.geojson"}>{t.geojson}</a>
          <a href={summary?.downloads.candidateJsonl ?? OBSERVATIONS_URL}>{t.observations}</a>
          <a href={summary?.downloads.cropManifest ?? "/data/reconstruction/full-pilot-response-evidence-crops.jsonl"}>{t.cropManifest}</a>
        </nav>
      </footer>
    </main>
  );
}
