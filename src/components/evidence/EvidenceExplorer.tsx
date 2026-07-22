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

type ExplorerTab = "findings" | "highlights" | "explorer" | "sources";
type SortMode = "strength" | "earliest" | "latest" | "cell";
type ImageMode = "native" | "enhanced";

interface MapActionResponseSite {
  id: string;
  name: string;
  documentedAsOf: string;
  datasetUrl: string;
  directlyAnnotatedServices: string[];
  sleepingEvidence: {
    annotatedSleepingAreas: number;
    description: string;
  } | null;
  aerialCrosscheck: {
    nearestCandidate: {
      cellId: string;
      distanceMeters: number;
      hoursAfterEvent: number | null;
      assetCategories: string[];
    } | null;
    earliestCrossModelShelterSignalWithin300m: {
      cellId: string;
      distanceMeters: number;
      hoursAfterEvent: number;
    } | null;
  };
}

interface MapActionResponseEvidence {
  headlineFindings: {
    mappedResponseSites: number;
    sitesWithAnnotatedSleepingAreas: number;
    annotatedSleepingAreas: number;
    capacityLabeledShelters: number;
    printedCapacityPeopleTotal: number;
    namedTemporaryWasteSites: number;
    healthFacilitiesWithPrintedWasteDistance: number;
  };
  responseSites: MapActionResponseSite[];
  debrisManagement: {
    documentedAsOf: string;
    namedTemporaryDisposalAndSortingSites: string[];
    healthFacilityDistances: Array<{
      facilityName: string;
      facilityType: string;
      distanceMeters: number;
    }>;
  };
  additionalImageryInventory: {
    sourceUrl: string;
    reportedImageCountApprox: number;
    limitation: string;
  };
}

const PAGE_SIZE = 24;
const SUMMARY_URL =
  "/data/reconstruction/full-pilot-evidence-explorer-summary.json";
const OBSERVATIONS_URL =
  "/data/reconstruction/full-pilot-response-evidence.jsonl";
const CURATED_URL =
  "/data/reconstruction/aerial-response-evidence-la-guaira.json";
const MAPACTION_RESPONSE_URL =
  "/data/reconstruction/mapaction-response-sites-la-guaira.json";
const CELL_DETAIL_BASE =
  "/data/reconstruction/full-pilot-evidence-cells";

const copy = {
  es: {
    title: "Qué muestran las imágenes",
    atlasLabel: "Atlas de evidencia aérea",
    eyebrow: "La Guaira · Caraballeda · Catia La Mar",
    dek: "Una lectura pública de cuándo y dónde se volvió visible la respuesta, seguida por los casos revisados y el inventario completo de señales candidatas.",
    back: "Volver a la cronología",
    map: "Abrir mapa de daños",
    candidates: "celdas candidatas",
    pairs: "pares de evidencia",
    reviewed: "casos revisados",
    within72: "visibles ≤72 h",
    findings: "Hallazgos",
    explorer: "Explorar 399",
    highlights: "Casos revisados",
    sources: "Método y fuentes",
    heroFindings: "Leer hallazgos",
    heroExplore: "Explorar detecciones",
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
    comparisonCount: "comparaciones publicadas",
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
    filters: "Filtros",
    showFilters: "Mostrar filtros",
    hideFilters: "Ocultar filtros",
    applyFilters: "Ver resultados",
    activeFilters: "filtros activos",
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
    findingsKicker: "Lectura pública · evidencia acotada",
    findingsTitle: "Lo que la evidencia permite sostener",
    findingsIntro:
      "La señal más útil no es el total de detecciones, sino cómo cambia la evidencia por tiempo, lugar y tipo de respuesta. Estos hallazgos combinan imágenes fechadas con fuentes de terreno; ninguno fija por sí solo una hora exacta de llegada.",
    canSay: "Lo que sí podemos decir",
    cannotSay: "Lo que todavía no podemos decir",
    earlySignalTitle: "La mayor expansión visible aparece entre 24 y 48 horas",
    earlySignalBody:
      "Diez celdas candidatas mostraron su primera señal visible durante las primeras 24 horas; 279 lo hicieron entre 24 y 48 horas. Esto describe la cobertura disponible y no prueba que la ayuda estuviera ausente antes.",
    trucksTitle: "Camiones y distribución ya eran observables en Catia La Mar el 26 de junio",
    trucksBody:
      "EFE reportó un contingente de camiones con ayuda y una terminal usada para distribuir alimentos y productos básicos. El reporte no permite fijar la hora exacta de llegada.",
    sitesTitle: "Los sitios temporales crecieron entre el 26 y el 29 de junio",
    sitesBody:
      "Las imágenes revisadas muestran un campo de golf ya organizado a +41 h y, para el 29 de junio, estadios, estacionamientos y pistas ocupados por módulos, vehículos o campamentos.",
    machineryTitle: "La maquinaria pesada no aparece de forma uniforme",
    machineryBody:
      "El 25 de junio se reportó disponibilidad limitada; el 28 se describió un aumento más amplio. El 29 todavía había al menos un sitio de colapso reportado sin maquinaria grande.",
    sourceBasis: "Base documental",
    imageBasis: "Base de imagen",
    firstVisibleWindows: "Primera señal visible en imágenes disponibles",
    firstVisibleWindowsIntro:
      "Las barras agrupan celdas candidatas por la ventana en que se volvieron visibles por primera vez. No son una medición de llegadas.",
    reviewedEvidenceTitle: "Evidencia revisada que ayuda a explicar la respuesta",
    reviewedEvidenceIntro:
      "Estos casos convierten píxeles y fechas en afirmaciones legibles, con límites explícitos.",
    viewAllReviewed: "Ver los 10 casos revisados",
    exploreAll: "Abrir las 399 candidatas",
    methodLink: "Revisar método y fuentes",
    noExactArrival:
      "No existe una adquisición continua ni una bitácora completa por sitio; por eso no podemos convertir «primera vez visible» en «hora de llegada».",
    noAbsence:
      "Una señal no observada puede quedar fuera de cobertura, ocultarse por nubes o no ser distinguible a esta resolución.",
    candidateDisclosure:
      "Los conteos son celdas candidatas de triage automatizado. Las categorías se superponen y no equivalen a objetos confirmados.",
    nativePolicy:
      "Los recortes de píxeles nativos son la vista de evidencia. Las imágenes mejoradas son solo para visualización y no pueden confirmar una característica.",
    arrivalPolicy:
      "Las fechas son límites de primera visibilidad en las adquisiciones disponibles, no horas reales de llegada.",
    absencePolicy:
      "No observado no significa que no haya ocurrido.",
    documentedSitesKicker: "MapAction · evidencia documental georreferenciada",
    documentedSitesTitle: "Dónde funcionó la respuesta",
    documentedSitesIntro:
      "Cinco mapas operativos ubican campamentos y servicios. Los cruzamos con la primera señal aérea candidata a menos de 300 metros; la coincidencia apoya la localización, no fija la hora de apertura.",
    mappedSites: "sitios de respuesta",
    sleepingAreas: "áreas de pernocta anotadas",
    printedCapacity: "capacidad impresa",
    capacityShelters: "refugios con capacidad",
    capacitySheltersShort: "refugios",
    wasteSites: "sitios temporales de residuos",
    documentedBy: "Documentado al",
    annotatedServices: "Servicios anotados directamente",
    sleepingLabel: "Pernocta",
    noSleepingLabel: "Sin área de pernocta anotada",
    aerialCrosscheck: "Cruce aéreo candidato",
    firstCrossModelSignal: "primera señal de refugio con ambos VLM",
    nearestCandidate: "candidata más cercana",
    hoursAfter: "h después del evento",
    mapActionSource: "Abrir mapa fuente",
    moreServices: "servicios más",
    debrisTitle: "Gestión de escombros y residuos",
    debrisBody:
      "Los productos cartográficos nombran 14 sitios temporales de disposición o clasificación al 16 de julio y publican distancias entre cinco centros de salud y sitios de residuos. Son registros de proximidad, no evidencia de impacto sanitario.",
    nearestHealthDistance: "menor distancia impresa a un centro de salud",
    imageryInventoryTitle: "El inventario conocido es mayor que la imagen pública descargable",
    imageryInventoryBody:
      "UN-SPIDER reportó aproximadamente 120 imágenes de varios proveedores. La mayoría circuló entre socios de respuesta y no tiene escena cruda pública; el atlas solo usa derivados públicos y metadatos.",
    publicationCaution:
      "No publicamos conteos visuales de carpas, módulos u ocupantes: MiniMax y Qwen produjeron rangos incompatibles en tres de cuatro campamentos. Conservamos únicamente etiquetas impresas, ubicaciones y servicios legibles en la fuente.",
    sourceDateCaution:
      "La leyenda de MA020 imprime 2027-07-03 en varias capas, una fecha incompatible con el evento. Usamos el 6 de julio de 2026 —fecha de publicación— como límite documental seguro y dejamos visible la anomalía.",
  },
  en: {
    title: "What the imagery shows",
    atlasLabel: "Aerial evidence atlas",
    eyebrow: "La Guaira · Caraballeda · Catia La Mar",
    dek: "A public reading of when and where response activity became visible, followed by reviewed cases and the complete candidate-signal inventory.",
    back: "Back to the timeline",
    map: "Open damage map",
    candidates: "candidate cells",
    pairs: "evidence pairs",
    reviewed: "reviewed cases",
    within72: "visible ≤72 h",
    findings: "Findings",
    explorer: "Explore 399",
    highlights: "Reviewed cases",
    sources: "Method & sources",
    heroFindings: "Read findings",
    heroExplore: "Explore detections",
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
    comparisonCount: "published comparisons",
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
    filters: "Filters",
    showFilters: "Show filters",
    hideFilters: "Hide filters",
    applyFilters: "View results",
    activeFilters: "active filters",
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
    findingsKicker: "Public reading · bounded evidence",
    findingsTitle: "What the evidence can support",
    findingsIntro:
      "The useful signal is not the raw detection total, but how evidence changes by time, place and response type. These findings combine dated imagery with field sources; neither establishes an exact arrival time on its own.",
    canSay: "What we can say",
    cannotSay: "What we still cannot say",
    earlySignalTitle: "The largest visible expansion appears between 24 and 48 hours",
    earlySignalBody:
      "Ten candidate cells first became visible during the first 24 hours; 279 did so between 24 and 48 hours. This describes available coverage and does not prove assistance was absent earlier.",
    trucksTitle: "Trucks and distribution were observable in Catia La Mar by June 26",
    trucksBody:
      "EFE reported a contingent of aid trucks and a terminal distributing food and basic goods. The report does not establish an exact arrival time.",
    sitesTitle: "Temporary response sites grew between June 26 and June 29",
    sitesBody:
      "Reviewed imagery shows an organized golf-course operation at +41 h and, by June 29, stadiums, parking lots and tracks occupied by modules, vehicles or camps.",
    machineryTitle: "Heavy machinery was not reported uniformly",
    machineryBody:
      "Availability was reported as limited on June 25; a broader increase was described on June 28. At least one reported collapse site still lacked large machinery on June 29.",
    sourceBasis: "Documentary basis",
    imageBasis: "Imagery basis",
    firstVisibleWindows: "First visible signal in available imagery",
    firstVisibleWindowsIntro:
      "Bars group candidate cells by the window in which they first became visible. They are not a measurement of arrivals.",
    reviewedEvidenceTitle: "Reviewed evidence that helps explain the response",
    reviewedEvidenceIntro:
      "These cases turn pixels and dates into readable claims with explicit limits.",
    viewAllReviewed: "View all 10 reviewed cases",
    exploreAll: "Open all 399 candidates",
    methodLink: "Review method and sources",
    noExactArrival:
      "There is no continuous acquisition or complete site-by-site operating log, so “first visible” cannot be converted into an arrival time.",
    noAbsence:
      "An unobserved signal may fall outside coverage, be obscured by clouds, or remain indistinguishable at this resolution.",
    candidateDisclosure:
      "Counts are automated-triage candidate cells. Categories overlap and do not equal confirmed objects.",
    nativePolicy:
      "Native crops are the evidence view. Enhanced images are display-only and cannot establish a feature.",
    arrivalPolicy:
      "Dates are earliest visible bounds in available acquisitions, not actual arrival times.",
    absencePolicy:
      "Not observed does not mean it did not occur.",
    documentedSitesKicker: "MapAction · georeferenced documentary evidence",
    documentedSitesTitle: "Where response operations functioned",
    documentedSitesIntro:
      "Five operational maps locate camps and services. We cross-checked them against the first aerial candidate signal within 300 metres; proximity supports the location, not an opening time.",
    mappedSites: "response sites",
    sleepingAreas: "annotated sleeping areas",
    printedCapacity: "printed capacity",
    capacityShelters: "capacity-labelled shelters",
    capacitySheltersShort: "shelters",
    wasteSites: "temporary waste sites",
    documentedBy: "Documented by",
    annotatedServices: "Directly annotated services",
    sleepingLabel: "Sleeping areas",
    noSleepingLabel: "No sleeping area annotated",
    aerialCrosscheck: "Candidate aerial cross-check",
    firstCrossModelSignal: "first shelter signal from both VLMs",
    nearestCandidate: "nearest candidate",
    hoursAfter: "h after the event",
    mapActionSource: "Open source map",
    moreServices: "more services",
    debrisTitle: "Debris and waste management",
    debrisBody:
      "Map products name 14 temporary disposal or sorting sites by July 16 and print distances between five health facilities and waste sites. These are proximity records, not evidence of health impact.",
    nearestHealthDistance: "shortest printed distance to a health facility",
    imageryInventoryTitle: "The known acquisition pool exceeds publicly downloadable imagery",
    imageryInventoryBody:
      "UN-SPIDER reported approximately 120 images from several providers. Most circulated among response partners without public raw scenes; the atlas uses only public derivatives and metadata.",
    publicationCaution:
      "We do not publish visual counts of tents, modules or occupants: MiniMax and Qwen produced incompatible ranges for three of four camps. Only printed labels, locations and source-readable services are retained.",
    sourceDateCaution:
      "The MA020 legend prints 2027-07-03 on several layers, a date incompatible with the event. We use July 6, 2026 —the publication date— as the safe documentary bound and disclose the anomaly.",
  },
} satisfies Record<EvidenceLanguage, Record<string, string>>;

const sourceLimitationsEs: Record<string, string> = {
  "eldiario-2026-06-25-la-guaira":
    "Algunas afirmaciones se atribuyen a residentes u otros reportes y no constituyen un inventario completo de la respuesta estatal.",
  "efe-2026-06-26-catia-aid":
    "El artículo no identifica la terminal y el reporte no permite establecer las condiciones de todos los sectores de Catia La Mar.",
  "wfp-2026-06-26-la-guaira":
    "Es un reporte a escala estatal, no una bitácora operativa sitio por sitio.",
  "logistics-cluster-2026-06-26":
    "La información operativa se describió como sujeta a cambios rápidos.",
  "efe-2026-06-29-playa-grande":
    "La ausencia de maquinaria grande corresponde a un sitio específico y no puede generalizarse a toda La Guaira.",
  "undp-2026-06-29-debris":
    "La estimación combina imágenes satelitales, evaluación de daños con IA y conocimiento de ingeniería; sirve para planificación, no como registro del despliegue de maquinaria.",
  "logistics-cluster-2026-07-02-sitrep":
    "Confirma la operación al 2 de julio, pero no la hora exacta de apertura de cada refugio.",
  "logistics-cluster-2026-07-02-minutes":
    "No aporta coordenadas exactas de los campamentos ni fechas de apertura para los 13 sitios de La Guaira.",
};

const sourceTypeEs: Record<string, string> = {
  "reported field account": "reporte de campo",
  "place-specific field reporting": "reporte de campo localizado",
  "primary humanitarian agency update": "actualización humanitaria primaria",
  "primary inter-agency meeting minutes": "minuta interagencial primaria",
  "primary UN assessment": "evaluación primaria de la ONU",
  "primary inter-agency situation report": "reporte de situación interagencial primario",
};

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

function consensusLabel(value: string, language: EvidenceLanguage) {
  const labels: Record<string, [string, string]> = {
    both_positive: ["Ambos modelos positivos", "Both models positive"],
    contested: ["Los modelos no coinciden", "Models disagree"],
    qwen_only: ["Solo Qwen positivo", "Qwen positive only"],
    minimax_only: ["Solo MiniMax positivo", "MiniMax positive only"],
  };
  return labels[value]?.[language === "es" ? 0 : 1] ?? value.replaceAll("_", " ");
}

function detectionLabel(value: string, language: EvidenceLanguage) {
  const labels: Record<string, [string, string]> = {
    Container: ["Contenedor", "Container"],
    Digger: ["Excavadora", "Digger"],
    LightVehicle: ["Vehículo liviano", "Light vehicle"],
    Truck: ["Camión", "Truck"],
  };
  return labels[value]?.[language === "es" ? 0 : 1] ?? value;
}

const windowFindings = [
  { key: "0_24h", label: "0–24 h", tone: "early" },
  { key: "24_48h", label: "24–48 h", tone: "surge" },
  { key: "48_72h", label: "48–72 h", tone: "early" },
  { key: "72h_7d", label: "72 h–7 d", tone: "late" },
  { key: "after_7d", label: ">7 d", tone: "late" },
] as const;

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
        <b>{detail.pairCount} {t.comparisonCount}</b>
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
          <dd>{consensusLabel(observation.consensus, language)}</dd>
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
              <b key={name}>{detectionLabel(name, language)} +{value}</b>
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
                <b>
                  {pair.targetDetection?.class
                    ? detectionLabel(pair.targetDetection.class, language)
                    : pair.pairId}
                </b>
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
        <p>{t.nativePolicy}</p>
        <p>{t.arrivalPolicy}</p>
        <p>{t.absencePolicy}</p>
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

function FindingsOverview({
  summary,
  curated,
  responseEvidence,
  language,
  onReviewed,
  onExplore,
  onSources,
}: {
  summary: EvidenceSummary;
  curated: CuratedEvidence | null;
  responseEvidence: MapActionResponseEvidence | null;
  language: EvidenceLanguage;
  onReviewed: () => void;
  onExplore: () => void;
  onSources: () => void;
}) {
  const t = copy[language];
  const maxWindow = Math.max(
    ...windowFindings.map(({ key }) => summary.timeWindowCounts[key] ?? 0),
  );
  const reviewedPreview = [
    "aerial-grid-caraballeda-golf",
    "aerial-grid-estadio-jorge-garcia",
    "aerial-ems-00119",
  ]
    .map((id) => curated?.observations.find((item) => item.id === id))
    .filter((item): item is CuratedObservation => Boolean(item));
  const findings = [
    {
      index: "01",
      title: t.earlySignalTitle,
      body: t.earlySignalBody,
      basis: `${t.imageBasis} · ${summary.timeWindowCounts["0_24h"] ?? 0} / ${summary.timeWindowCounts["24_48h"] ?? 0}`,
      tone: "image",
    },
    {
      index: "02",
      title: t.trucksTitle,
      body: t.trucksBody,
      basis: `${t.sourceBasis} · EFE · 26 jun 2026`,
      tone: "source",
    },
    {
      index: "03",
      title: t.sitesTitle,
      body: t.sitesBody,
      basis: `${t.imageBasis} · +41 h / 29 jun 2026`,
      tone: "image",
    },
    {
      index: "04",
      title: t.machineryTitle,
      body: t.machineryBody,
      basis: `${t.sourceBasis} · El Diario / EFE`,
      tone: "source",
    },
  ];

  return (
    <section className={styles.findings} aria-labelledby="findings-title">
      <header className={styles.findingsHeader}>
        <div>
          <span>{t.findingsKicker}</span>
          <h2 id="findings-title">{t.findingsTitle}</h2>
        </div>
        <p>{t.findingsIntro}</p>
      </header>

      <div className={styles.findingGrid}>
        {findings.map((finding) => (
          <article
            key={finding.index}
            className={styles.findingCard}
            data-tone={finding.tone}
          >
            <span>{finding.index}</span>
            <h3>{finding.title}</h3>
            <p>{finding.body}</p>
            <small>{finding.basis}</small>
          </article>
        ))}
      </div>

      <div className={styles.findingLimits}>
        <article>
          <span>{t.canSay}</span>
          <p>{t.candidateDisclosure}</p>
        </article>
        <article>
          <span>{t.cannotSay}</span>
          <p>{t.noExactArrival}</p>
          <p>{t.noAbsence}</p>
        </article>
      </div>

      {responseEvidence && (
        <section
          className={styles.documentedResponse}
          aria-labelledby="documented-response-title"
        >
          <header>
            <div>
              <span>{t.documentedSitesKicker}</span>
              <h3 id="documented-response-title">{t.documentedSitesTitle}</h3>
            </div>
            <p>{t.documentedSitesIntro}</p>
          </header>

          <dl className={styles.responseStats}>
            <div>
              <dt>{formatNumber(responseEvidence.headlineFindings.mappedResponseSites, language)}</dt>
              <dd>{t.mappedSites}</dd>
            </div>
            <div>
              <dt>{formatNumber(responseEvidence.headlineFindings.annotatedSleepingAreas, language)}</dt>
              <dd>{t.sleepingAreas}</dd>
            </div>
            <div>
              <dt>{formatNumber(responseEvidence.headlineFindings.printedCapacityPeopleTotal, language)}</dt>
              <dd>{t.printedCapacity} · {responseEvidence.headlineFindings.capacityLabeledShelters} {t.capacitySheltersShort}</dd>
            </div>
            <div>
              <dt>{formatNumber(responseEvidence.headlineFindings.namedTemporaryWasteSites, language)}</dt>
              <dd>{t.wasteSites}</dd>
            </div>
          </dl>

          <div className={styles.responseSiteGrid}>
            {responseEvidence.responseSites.map((site) => {
              const crossModel =
                site.aerialCrosscheck.earliestCrossModelShelterSignalWithin300m;
              const nearest = site.aerialCrosscheck.nearestCandidate;
              const services = site.directlyAnnotatedServices.slice(0, 4);
              return (
                <article key={site.id} className={styles.responseSiteCard}>
                  <div className={styles.responseSiteMeta}>
                    <span>MapAction · {site.documentedAsOf}</span>
                    <strong>
                      {site.sleepingEvidence?.annotatedSleepingAreas
                        ? `${site.sleepingEvidence.annotatedSleepingAreas} ${t.sleepingAreas}`
                        : t.noSleepingLabel}
                    </strong>
                  </div>
                  <h4>{site.name}</h4>
                  <div>
                    <b>{t.annotatedServices}</b>
                    {services.length ? (
                      <ul>
                        {services.map((service) => <li key={service}>{service}</li>)}
                      </ul>
                    ) : (
                      <p>—</p>
                    )}
                    {site.directlyAnnotatedServices.length > services.length && (
                      <small>
                        +{site.directlyAnnotatedServices.length - services.length} {t.moreServices}
                      </small>
                    )}
                  </div>
                  <div className={styles.aerialMatch}>
                    <b>VLM · {t.aerialCrosscheck}</b>
                    <p>
                      {crossModel
                        ? `${t.firstCrossModelSignal}: +${crossModel.hoursAfterEvent.toFixed(1)} ${t.hoursAfter} · ${Math.round(crossModel.distanceMeters)} m`
                        : nearest
                          ? `${t.nearestCandidate}: ${Math.round(nearest.distanceMeters)} m`
                          : "—"}
                    </p>
                  </div>
                  <a href={site.datasetUrl} target="_blank" rel="noreferrer">
                    {t.mapActionSource} ↗
                  </a>
                </article>
              );
            })}
          </div>

          <div className={styles.responseExtensions}>
            <article>
              <span>{responseEvidence.debrisManagement.documentedAsOf}</span>
              <h4>{t.debrisTitle}</h4>
              <p>{t.debrisBody}</p>
              <strong>
                {Math.min(
                  ...responseEvidence.debrisManagement.healthFacilityDistances.map(
                    (facility) => facility.distanceMeters,
                  ),
                )} m
              </strong>
              <small>{t.nearestHealthDistance}</small>
            </article>
            <article>
              <span>UN-SPIDER · ~{responseEvidence.additionalImageryInventory.reportedImageCountApprox}</span>
              <h4>{t.imageryInventoryTitle}</h4>
              <p>{t.imageryInventoryBody}</p>
              <a
                href={responseEvidence.additionalImageryInventory.sourceUrl}
                target="_blank"
                rel="noreferrer"
              >
                {t.openSource} ↗
              </a>
            </article>
          </div>

          <aside className={styles.responseCautions}>
            <p>{t.publicationCaution}</p>
            <p>{t.sourceDateCaution}</p>
          </aside>
        </section>
      )}

      <section className={styles.evidenceClock} aria-labelledby="evidence-clock-title">
        <header>
          <div>
            <span>0–257 h</span>
            <h3 id="evidence-clock-title">{t.firstVisibleWindows}</h3>
          </div>
          <p>{t.firstVisibleWindowsIntro}</p>
        </header>
        <div className={styles.windowBars}>
          {windowFindings.map(({ key, label, tone }) => {
            const value = summary.timeWindowCounts[key] ?? 0;
            return (
              <article key={key} data-tone={tone}>
                <div>
                  <span>{label}</span>
                  <strong>{formatNumber(value, language)}</strong>
                </div>
                <div aria-hidden="true">
                  <i style={{ width: `${Math.max(2, (value / maxWindow) * 100)}%` }} />
                </div>
                <button type="button" onClick={onExplore}>
                  {t.exploreAll} →
                </button>
              </article>
            );
          })}
        </div>
        <small>{t.candidateDisclosure}</small>
      </section>

      <section className={styles.reviewedPreview} aria-labelledby="reviewed-preview-title">
        <header>
          <div>
            <span>3 / 10</span>
            <h3 id="reviewed-preview-title">{t.reviewedEvidenceTitle}</h3>
          </div>
          <p>{t.reviewedEvidenceIntro}</p>
        </header>
        {reviewedPreview.length ? (
          <div className={styles.reviewedPreviewGrid}>
            {reviewedPreview.map((observation) => (
              <HighlightCard
                key={observation.id}
                observation={observation}
                language={language}
              />
            ))}
          </div>
        ) : (
          <p className={styles.status}>{t.loading}</p>
        )}
      </section>

      <nav className={styles.findingActions} aria-label={t.findingsTitle}>
        <button type="button" onClick={onReviewed}>{t.viewAllReviewed} →</button>
        <button type="button" onClick={onExplore}>{t.exploreAll} →</button>
        <button type="button" onClick={onSources}>{t.methodLink} →</button>
      </nav>
    </section>
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
  const [responseEvidence, setResponseEvidence] =
    useState<MapActionResponseEvidence | null>(null);
  const [loading, setLoading] = useState(true);
  const [observationsLoaded, setObservationsLoaded] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [tab, setTab] = useState<ExplorerTab>("findings");
  const [filtersOpen, setFiltersOpen] = useState(false);
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
  const initialCellRef = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const initialCell = new URLSearchParams(window.location.search).get("cell");
    initialCellRef.current = initialCell;
    Promise.all([
      fetch(SUMMARY_URL, { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error(`summary:${response.status}`);
        return response.json() as Promise<EvidenceSummary>;
      }),
      fetch(CURATED_URL, { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error(`curated:${response.status}`);
        return response.json() as Promise<CuratedEvidence>;
      }),
      fetch(MAPACTION_RESPONSE_URL, { signal: controller.signal })
        .then((response) => {
          if (!response.ok) throw new Error(`mapaction:${response.status}`);
          return response.json() as Promise<MapActionResponseEvidence>;
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === "AbortError") {
            throw error;
          }
          return null;
        }),
    ])
      .then(([nextSummary, nextCurated, nextResponseEvidence]) => {
        setSummary(nextSummary);
        setCurated(nextCurated);
        setResponseEvidence(nextResponseEvidence);
        if (initialCell) setTab("explorer");
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
    if (tab !== "explorer" || observationsLoaded) return;
    const controller = new AbortController();
    fetch(OBSERVATIONS_URL, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`observations:${response.status}`);
        return parseJsonl<EvidenceObservation>(await response.text());
      })
      .then((nextObservations) => {
        setObservations(nextObservations);
        setObservationsLoaded(true);
        const initialCell = initialCellRef.current;
        if (initialCell && nextObservations.some((row) => row.cellId === initialCell)) {
          setDetailLoading(true);
          setDetailError(false);
          setDetail(null);
          setSelectedCellId(initialCell);
          initialCellRef.current = null;
        }
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setLoadError(true);
        }
      });
    return () => controller.abort();
  }, [tab, observationsLoaded]);

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
  const activeFilterCount = [
    query.trim() ? "query" : "",
    category !== "all" ? category : "",
    agreement !== "all" ? agreement : "",
    timeWindow !== "all" ? timeWindow : "",
    imagery !== "all" ? imagery : "",
  ].filter(Boolean).length;

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

  const openTab = (nextTab: ExplorerTab) => {
    setTab(nextTab);
    requestAnimationFrame(() => {
      document.getElementById(`${nextTab}-panel`)?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
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
          <b>{t.atlasLabel}</b>
          <h1>{t.title}</h1>
          <span>{t.dek}</span>
          <div className={styles.heroActions}>
            <button type="button" onClick={() => openTab("findings")}>
              {t.heroFindings} →
            </button>
            <button type="button" onClick={() => openTab("explorer")}>
              {t.heroExplore}
            </button>
          </div>
        </div>
        <dl className={styles.heroStats}>
          <div>
            <dt>{summary?.coverage.withinFirst72Hours ?? 311}</dt>
            <dd>{t.within72} · {t.candidates}</dd>
          </div>
          <div>
            <dt>{summary?.assetCategoryCounts.heavy_machinery ?? 75}</dt>
            <dd>{t.machinery} · {t.candidates}</dd>
          </div>
          <div>
            <dt>{summary?.assetCategoryCounts.trucks_or_large_vehicles ?? 128}</dt>
            <dd>{t.trucks} · {t.candidates}</dd>
          </div>
          <div>
            <dt>
              {(summary?.evidenceTierCounts.cross_model_positive ?? 33) +
                (summary?.evidenceTierCounts.cross_model_positive_with_detector_delta ?? 71)}
            </dt>
            <dd>{t.bothPositive}</dd>
          </div>
        </dl>
      </header>

      <aside className={styles.triageWarning}>
        <b>{t.triage}</b>
        <p>{t.triageText}</p>
        <span>Qwen · MiniMax · WALDO30</span>
      </aside>

      <div className={styles.tabRail} role="tablist" aria-label={t.title}>
        {([
          ["findings", t.findings, "01"],
          ["highlights", t.highlights, "10"],
          ["explorer", t.explorer, "399"],
          ["sources", t.sources, "08"],
        ] as const).map(([value, label, count]) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={tab === value}
            aria-controls={`${value}-panel`}
            aria-label={label}
            onClick={() => openTab(value)}
          >
            <span aria-hidden="true">{count}</span>
            {label}
          </button>
        ))}
      </div>

      {tab === "findings" && (
        <div id="findings-panel" role="tabpanel">
          {loading && <p className={styles.status} aria-live="polite">{t.loading}</p>}
          {loadError && <p className={`${styles.status} ${styles.error}`} role="alert">{t.error}</p>}
          {summary && (
            <FindingsOverview
              summary={summary}
              curated={curated}
              responseEvidence={responseEvidence}
              language={language}
              onReviewed={() => openTab("highlights")}
              onExplore={() => openTab("explorer")}
              onSources={() => openTab("sources")}
            />
          )}
        </div>
      )}

      {tab === "explorer" && (
        <section
          id="explorer-panel"
          className={styles.explorer}
          role="tabpanel"
          aria-labelledby="all-candidates-title"
        >
          <div className={styles.explorerIntro}>
            <div>
              <span>399 / 500</span>
              <h2>{t.explorer}</h2>
            </div>
            <p>{t.candidateDisclosure}</p>
          </div>
          <button
            className={styles.filterToggle}
            type="button"
            aria-expanded={filtersOpen}
            aria-controls="candidate-filters"
            onClick={() => setFiltersOpen((open) => !open)}
          >
            <b>{filtersOpen ? t.hideFilters : t.showFilters}</b>
            {activeFilterCount > 0 && (
              <span>{activeFilterCount} {t.activeFilters}</span>
            )}
          </button>
          <div
            id="candidate-filters"
            className={styles.filters}
            data-open={filtersOpen ? "true" : "false"}
          >
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
            <button
              className={styles.applyFilters}
              type="button"
              onClick={() => {
                setFiltersOpen(false);
                requestAnimationFrame(() => resultHeadingRef.current?.focus());
              }}
            >
              {t.applyFilters} →
            </button>
          </div>

          {!observationsLoaded && <p className={styles.status} aria-live="polite">{t.loading}</p>}
          {loadError && <p className={`${styles.status} ${styles.error}`} role="alert">{t.error}</p>}

          {observationsLoaded && observations.length > 0 && (
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
                              {observation.stackStatus === "before_after" ? t.beforeAfter : t.postOnly}
                            </span>
                          </div>
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
                {selectedCellId && (
                  <DetailPanel
                    detail={detail}
                    loading={detailLoading}
                    error={detailError}
                    language={language}
                    onClose={closeDetail}
                  />
                )}
              </div>
            </>
          )}
        </section>
      )}

      {tab === "highlights" && (
        <section
          id="highlights-panel"
          className={styles.editorialSection}
          role="tabpanel"
          aria-labelledby="reviewed-title"
        >
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

      {tab === "sources" && summary && (
        <section
          id="sources-panel"
          className={styles.editorialSection}
          role="tabpanel"
          aria-labelledby="sources-title"
        >
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
                <span>
                  {String(index + 1).padStart(2, "0")} ·{" "}
                  {language === "es"
                    ? sourceTypeEs[source.sourceType] ?? source.sourceType
                    : source.sourceType}
                </span>
                <h3>{source.publisher}</h3>
                <time>{source.publishedAt.slice(0, 10)}</time>
                <ul>
                  {(language === "es" ? source.claimsEs ?? source.claims : source.claims).map((claim) => (
                    <li key={claim}>{claim}</li>
                  ))}
                </ul>
                <p>
                  {language === "es"
                    ? sourceLimitationsEs[source.id] ?? source.limitations
                    : source.limitations}
                </p>
                <a href={source.url} target="_blank" rel="noreferrer">{t.openSource} ↗</a>
              </article>
            ))}
          </div>
        </section>
      )}

      <footer className={styles.footer}>
        <div>
          <b>{t.downloads}</b>
          <p>{t.arrivalPolicy}</p>
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
