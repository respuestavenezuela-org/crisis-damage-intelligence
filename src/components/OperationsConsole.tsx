"use client";

import { type RefObject, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { trackAnalytics } from "@/lib/analytics";
import { cn } from "@/lib/utils";
import MapPanel from "./map/MapPanel";
import type { AoiCatalog, AoiRecord, DamageFeature, Language, VlmRecord } from "./types";

const DIRECT_RASTER_MOBILE_MAX_BYTES = 250_000_000;

const copy = {
  en: {
    title: "Respuesta Venezuela",
    subtitle: "Geospatial damage triage for earthquake response",
    live: "Public read-only",
    language: "Language",
    aoi: "Go to affected area",
    quickStart: "Start with La Guaira · open Priority · tap red structures",
    rankingNote: "Ranked by response value: official EMS destroyed/damaged first, then possible/MONIT01, VLM triage, and capped external predictions.",
    source: "Source",
    status: "Status",
    features: "features",
    candidates: "candidates",
    confirmed: "official destroyed/damaged",
    possible: "official possible",
    vlm: "VLM before/after",
    vlmPostEvent: "VLM post-event",
    mode: "Image",
    basemap: "Base",
    mapBase: "Map",
    aerialBase: "Aerial",
    aerialBaseNote: "Reference imagery only. Damage evidence comes from EMS vectors and post-event AOI imagery.",
    before: "Before",
    after: "After",
    noImagery: "No imagery exposed for this AOI yet",
    noBefore: "Before imagery is not exposed yet. Showing post-event imagery where available.",
    approximateBefore: "Before shows external aerial reference only; not official EMS and not guaranteed pre-event.",
    beforeEvidenceOnly: "Before reference exists for evidence chips only; no before map layer is published.",
    imageryAvailable: "Post-event imagery available",
    imageryCoverage: "Imagery coverage",
    afterImagery: "After imagery",
    beforeImagery: "Before imagery",
    mapLayerAvailable: "Map layer available",
    evidenceOnly: "Evidence chips only",
    notAvailable: "Not available",
    officialAfter: "Copernicus EMS post-event imagery",
    nonOfficialBefore: "Public/OpenData reference - not official EMS imagery",
    coverage: "Coverage",
    imageryOnly: "Imagery only - no official damage vector yet",
    opacity: "Damage opacity",
    filters: "Filters",
    controls: "Controls",
    all: "All",
    severe: "Destroyed/Damaged",
    vlmOnly: "VLM reviewed",
    filterNote: "Severity uses official EMS damage_gra when available. Possible damage is not counted as destroyed/damaged.",
    downloads: "Downloads",
    evidence: "Evidence queue",
    operationalBrief: "Operational brief",
    recommendedAction: "Recommended action",
    reviewPriority: "Review priority",
    fieldDownloads: "Field downloads",
    priorityReady: "priority rows ready",
    noPriorityReady: "No priority rows loaded yet",
    officialBrief: "Use official EMS damage first, then VLM evidence to decide what needs a closer look.",
    monitorBrief: "Use official MONIT01 points as field leads; keep them separate from EMS building-vector counts.",
    imageryBrief: "Use this AOI for visual context only. No official damage vector is published yet.",
    externalBrief: "Use this as a search lead only. Do not count it as official damage.",
    downloadField: "Field packet",
    downloadGis: "GIS data",
    downloadEvidence: "Evidence",
    downloadImagery: "Imagery",
    downloadOther: "Other",
    lightModeHint: "For weak links, start with KML/CSV and open imagery only when needed.",
    loadingCatalog: "Loading AOI catalog...",
    catalogError: "Catalog unavailable. The static shell is still available; retry or use published downloads if already cached.",
    loadingDamage: "Loading active AOI damage layer...",
    damageError: "Damage geometry failed to load. Use metadata and downloads; the app shell remains usable.",
    loadingVlm: "Loading VLM evidence for active AOI...",
    vlmError: "VLM evidence failed to load. Official EMS vectors and downloads remain the source of record.",
    backToPriority: "Back to priority list",
    noSelection: "Select a polygon to inspect evidence.",
    watchlist: "Incoming products",
    architecture: "Low-cost operating model",
    architectureText:
      "Vercel serves the shell. Public AOI data is static GeoJSON/CSV/KML. Rasters and chips should move to R2/Supabase Storage. Supabase/PostGIS is optional for tracking and review, not required for public read-only loads.",
    chip: "Open evidence chip",
    maps: "Google Maps",
    officialData: "Operational EMSR884 data",
    externalPrediction: "External predicted damage - triage only",
    demoOnly: "Demo/VLM benchmark - not Venezuela operational data",
    confidenceTitle: "Data confidence",
    confidenceText:
      "Official EMS vector labels are the source of record for this AOI. MiniMax-M3 VLM results are triage aids. When before/after chips are available, the VLM compares visible change; otherwise it is lower-confidence post-event-only review.",
    vlmQualityTitle: "VLM before/after quality",
    vlmCoverage: "reviewed",
    vlmSkipped: "skipped no-before",
    vlmUncertain: "uncertain",
    vlmActionable: "visible-change signals",
    vlmUrgent: "urgent review",
    vlmQualityNote:
      "VLM signals are triage aids only. High uncertainty means the imagery pair could not support a reliable damage call.",
    statuses: {
      "test-fixture": "Readiness test",
      "official-vector": "Official EMS vector",
      "official-monitor-points": "Official EMS monitor points",
      "external-prediction": "External prediction",
      "imagery-only": "Imagery only",
      waiting: "Waiting",
      "in-production": "In production",
      "no-official-product": "No official EMS product",
      "external-gap": "External gap to source",
    },
  },
  es: {
    title: "Respuesta Venezuela",
    subtitle: "Triage geoespacial de daños para respuesta al terremoto",
    live: "Público solo lectura",
    language: "Idioma",
    aoi: "Ir a zona afectada",
    quickStart: "Empieza por La Guaira · abre Prioridad · toca estructuras rojas",
    rankingNote: "Ordenado por valor de respuesta: primero destruido/dañado oficial EMS, luego posible/MONIT01, triage VLM y predicciones externas limitadas.",
    source: "Fuente",
    status: "Estado",
    features: "estructuras",
    candidates: "candidatos",
    confirmed: "destruidos/dañados oficiales",
    possible: "posibles oficiales",
    vlm: "VLM antes/después",
    vlmPostEvent: "VLM post-evento",
    mode: "Imagen",
    basemap: "Base",
    mapBase: "Mapa",
    aerialBase: "Aérea",
    aerialBaseNote: "Imagen de referencia solamente. La evidencia de daño viene de vectores EMS e imagen posterior por AOI.",
    before: "Antes",
    after: "Después",
    noImagery: "Sin imagen expuesta para este AOI todavía",
    noBefore: "La imagen antes no está expuesta todavía. Se muestra imagen posterior donde exista.",
    approximateBefore: "Antes muestra solo referencia aérea externa; no es oficial EMS ni garantiza fecha pre-evento.",
    beforeEvidenceOnly: "Existe referencia antes para chips de evidencia; no hay capa antes publicada en el mapa.",
    imageryAvailable: "Imagen posterior disponible",
    imageryCoverage: "Cobertura de imagenes",
    afterImagery: "Imagen después",
    beforeImagery: "Imagen antes",
    mapLayerAvailable: "Capa de mapa disponible",
    evidenceOnly: "Solo chips de evidencia",
    notAvailable: "No disponible",
    officialAfter: "Imagen post-evento de Copernicus EMS",
    nonOfficialBefore: "Referencia publica/OpenData - no es imagen oficial EMS",
    coverage: "Cobertura",
    imageryOnly: "Solo imagen - sin vector oficial de danos aun",
    opacity: "Opacidad de daño",
    filters: "Filtros",
    controls: "Controles",
    all: "Todos",
    severe: "Destruido/Dañado",
    vlmOnly: "Revisado VLM",
    filterNote: "La severidad usa damage_gra oficial de EMS cuando existe. Posible daño no cuenta como destruido/dañado.",
    downloads: "Descargas",
    evidence: "Cola de evidencia",
    operationalBrief: "Brief operativo",
    recommendedAction: "Acción recomendada",
    reviewPriority: "Ver prioridad",
    fieldDownloads: "Descargas de campo",
    priorityReady: "filas de prioridad listas",
    noPriorityReady: "Aún no hay filas de prioridad cargadas",
    officialBrief: "Usa primero el daño oficial EMS y luego la evidencia VLM para decidir qué revisar con más detalle.",
    monitorBrief: "Usa los puntos oficiales MONIT01 como pistas de campo; mantenlos separados de los conteos vectoriales EMS.",
    imageryBrief: "Usa este AOI solo como contexto visual. Aún no hay vector oficial de daños publicado.",
    externalBrief: "Usa esto solo como pista de búsqueda. No lo cuentes como daño oficial.",
    downloadField: "Paquete de campo",
    downloadGis: "Datos GIS",
    downloadEvidence: "Evidencia",
    downloadImagery: "Imagen",
    downloadOther: "Otros",
    lightModeHint: "Con enlace débil, empieza con KML/CSV y abre imagen solo cuando haga falta.",
    loadingCatalog: "Cargando catálogo de AOIs...",
    catalogError: "Catálogo no disponible. La interfaz estática sigue disponible; reintenta o usa descargas publicadas si ya están en caché.",
    loadingDamage: "Cargando capa de daños del AOI activo...",
    damageError: "No se pudo cargar la geometría de daños. Usa metadatos y descargas; la interfaz sigue usable.",
    loadingVlm: "Cargando evidencia VLM del AOI activo...",
    vlmError: "No se pudo cargar evidencia VLM. Los vectores EMS oficiales y descargas siguen siendo la fuente principal.",
    backToPriority: "Volver a prioridad",
    noSelection: "Selecciona un poligono para inspeccionar evidencia.",
    watchlist: "Productos entrantes",
    architecture: "Modelo operativo de bajo costo",
    architectureText:
      "Vercel sirve la interfaz. Los datos publicos por AOI son GeoJSON/CSV/KML estaticos. Rasters y chips deben ir a R2/Supabase Storage. Supabase/PostGIS es opcional para tracking y validacion, no requerido para la carga publica.",
    chip: "Abrir chip de evidencia",
    maps: "Google Maps",
    officialData: "Datos operativos EMSR884",
    externalPrediction: "Predicción externa de daño - solo triage",
    demoOnly: "Demo/benchmark VLM - no es dato operativo de Venezuela",
    confidenceTitle: "Confianza del dato",
    confidenceText:
      "Las etiquetas vectoriales oficiales de EMS son la fuente principal para este AOI. Los resultados MiniMax-M3 son ayudas de triage. Cuando existen chips antes/después, el VLM compara cambio visible; si no, es revisión post-evento de menor confianza.",
    vlmQualityTitle: "Calidad VLM antes/después",
    vlmCoverage: "revisados",
    vlmSkipped: "sin antes",
    vlmUncertain: "inciertos",
    vlmActionable: "señales de cambio visible",
    vlmUrgent: "revisión urgente",
    vlmQualityNote:
      "Las señales VLM son solo ayuda de triage. Alta incertidumbre significa que el par de imágenes no permite una llamada de daño confiable.",
    statuses: {
      "test-fixture": "Prueba de preparación",
      "official-vector": "Vector oficial EMS",
      "official-monitor-points": "Puntos oficiales EMS monitor",
      "external-prediction": "Predicción externa",
      "imagery-only": "Solo imagen",
      waiting: "En espera",
      "in-production": "En producción",
      "no-official-product": "Sin producto oficial EMS",
      "external-gap": "Brecha externa por cubrir",
    },
  },
};

type Filter = "all" | "severe" | "vlm";
type Mode = "before" | "after";
type Basemap = "map" | "aerial";
type LoadStatus = "idle" | "loading" | "ready" | "error";
type AoiLayerState = {
  damage?: LoadStatus;
  vlm?: LoadStatus;
};
type CityNavItem = {
  id: string;
  primaryAoiId: string;
  sourceIds: string[];
  name: Record<Language, string>;
  official: number;
  officialConfirmed: number;
  officialPossible: number;
  monitor: number;
  monitorConfirmed: number;
  monitorPossible: number;
  external: number;
  vlmBeforeAfterCritical: number;
  imageryOnly: boolean;
  score: number;
};

let appLoadedTracked = false;

const n = (value: unknown) => Number(value ?? 0) || 0;
const interactionClockMs = () => performance.now();
const isSmallViewport = () => typeof window !== "undefined" && window.matchMedia("(max-width: 760px)").matches;

const cityGroups: Array<Omit<
  CityNavItem,
  | "official"
  | "officialConfirmed"
  | "officialPossible"
  | "monitor"
  | "monitorConfirmed"
  | "monitorPossible"
  | "external"
  | "vlmBeforeAfterCritical"
  | "imageryOnly"
  | "score"
>> = [
  {
    id: "la-guaira",
    primaryAoiId: "emsr884-aoi12-caraballeda",
    sourceIds: [
      "emsr884-aoi12-caraballeda",
      "emsr884-aoi12-caraballeda-monitor01",
      "external-msft-catia-la-mar-predicted-damage",
      "external-msft-caraballeda-east-predicted-damage",
      "external-msft-catia-la-mar-east-predicted-damage",
      "external-msft-la-guaira-east-predicted-damage",
    ],
    name: { en: "La Guaira / Caraballeda / Catia La Mar", es: "La Guaira / Caraballeda / Catia La Mar" },
  },
  {
    id: "san-felipe",
    primaryAoiId: "emsr884-aoi08-san-felipe",
    sourceIds: ["emsr884-aoi08-san-felipe", "emsr884-aoi08-san-felipe-monitor01"],
    name: { en: "San Felipe", es: "San Felipe" },
  },
  {
    id: "santa-cruz",
    primaryAoiId: "emsr884-aoi05-santa-cruz",
    sourceIds: ["emsr884-aoi05-santa-cruz"],
    name: { en: "Santa Cruz", es: "Santa Cruz" },
  },
  {
    id: "moron",
    primaryAoiId: "emsr884-aoi06-moron",
    sourceIds: ["emsr884-aoi06-moron", "emsr884-aoi06-moron-monitor01"],
    name: { en: "Moron", es: "Morón" },
  },
  {
    id: "caracas",
    primaryAoiId: "emsr884-aoi02-caracas",
    sourceIds: ["emsr884-aoi02-caracas", "emsr884-aoi02-caracas-monitor01"],
    name: { en: "Caracas", es: "Caracas" },
  },
  {
    id: "antimano",
    primaryAoiId: "emsr884-aoi03-antimano",
    sourceIds: ["emsr884-aoi03-antimano"],
    name: { en: "Antimano", es: "Antímano" },
  },
  {
    id: "guacara",
    primaryAoiId: "emsr884-aoi10-guacara",
    sourceIds: ["emsr884-aoi10-guacara"],
    name: { en: "Guacara", es: "Guacara" },
  },
];

function cityImpactLabel(item: CityNavItem, language: Language) {
  if (item.imageryOnly) return language === "es" ? "Imagen disponible · 0 daños oficiales" : "Imagery available · 0 official damage";
  const parts: string[] = [];
  if (item.officialConfirmed) parts.push(language === "es" ? `${item.officialConfirmed} destruidos/dañados oficiales` : `${item.officialConfirmed} official destroyed/damaged`);
  if (item.officialPossible) parts.push(language === "es" ? `${item.officialPossible} posibles oficiales` : `${item.officialPossible} official possible`);
  if (item.monitor) parts.push(language === "es" ? `${item.monitor} MONIT01` : `${item.monitor} MONIT01`);
  if (item.vlmBeforeAfterCritical) parts.push(language === "es" ? `${item.vlmBeforeAfterCritical} VLM antes/después` : `${item.vlmBeforeAfterCritical} VLM before/after`);
  if (item.external) parts.push(language === "es" ? `${item.external} externos solo triage` : `${item.external} external triage-only`);
  return parts.join(" · ") || (language === "es" ? "0 daños oficiales" : "0 official damage");
}

function cityResponseScore(records: AoiRecord[]) {
  const officialVectors = records.filter((aoi) => aoi.status === "official-vector");
  const monitorLayers = records.filter((aoi) => aoi.status === "official-monitor-points");
  const externalLayers = records.filter((aoi) => aoi.status === "external-prediction");
  const imageryOnly = records.length > 0 && records.every((aoi) => aoi.status === "imagery-only");
  const official = officialVectors.reduce((sum, aoi) => sum + n(aoi.metrics.features), 0);
  const officialConfirmed = officialVectors.reduce((sum, aoi) => sum + n(aoi.metrics.damagedConfirmed), 0);
  const officialPossible = officialVectors.reduce((sum, aoi) => sum + n(aoi.metrics.possibleDamage), 0);
  const monitor = monitorLayers.reduce((sum, aoi) => sum + n(aoi.metrics.features), 0);
  const monitorConfirmed = monitorLayers.reduce((sum, aoi) => sum + n(aoi.metrics.damagedConfirmed), 0);
  const monitorPossible = monitorLayers.reduce((sum, aoi) => sum + n(aoi.metrics.possibleDamage), 0);
  const external = externalLayers.reduce((sum, aoi) => sum + n(aoi.metrics.candidates ?? aoi.metrics.features), 0);
  const vlmBeforeAfterCritical = officialVectors.reduce(
    (sum, aoi) => sum + n(aoi.metrics.vlmBeforeAfterLikelyDestroyed) + n(aoi.metrics.vlmBeforeAfterPossibleMajor),
    0,
  );
  return {
    official,
    officialConfirmed,
    officialPossible,
    monitor,
    monitorConfirmed,
    monitorPossible,
    external,
    vlmBeforeAfterCritical,
    imageryOnly,
    score:
      officialConfirmed * 1_000 +
      officialPossible * 180 +
      monitorConfirmed * 140 +
      monitorPossible * 90 +
      vlmBeforeAfterCritical * 55 +
      Math.min(external * 0.01, 75) +
      (imageryOnly ? 1 : 0),
  };
}

function officialSeverityScore(cls: string) {
  const normalized = cls.toLowerCase();
  if (normalized.includes("destroy")) return 12_000;
  if (normalized.includes("possibly")) return 8_000;
  if (normalized.includes("damage") || normalized.includes("major")) return 11_000;
  if (normalized.includes("minor")) return 7_000;
  return 0;
}

function vlmSeverityScore(vlm?: VlmRecord) {
  const cls = String(vlm?.vlm?.damage_class ?? "").toLowerCase();
  const reviewType = String(vlm?.vlm?.review_type ?? vlm?.review_type ?? "");
  const beforeAfterBonus = reviewType.includes("before") || reviewType.includes("comparison") ? 300 : 0;
  if (cls.includes("likely_destroyed") || cls.includes("likely destroyed")) return 5_200 + beforeAfterBonus;
  if (cls.includes("possible_major") || cls.includes("possible major")) return 4_700 + beforeAfterBonus;
  if (cls.includes("minor")) return 3_700 + beforeAfterBonus;
  return vlm ? 3_000 + beforeAfterBonus : 0;
}

function priorityFeatureScore(feature: DamageFeature, vlm?: VlmRecord, status?: string) {
  const p = feature.properties;
  const cls = String(p.damage_class ?? p.damage_gra ?? p.confirmed_damage_class ?? "");
  const numeric = n(p.damage_score ?? p.damage_percent ?? p.confirmed_damage_percent);
  if (status === "official-vector") return officialSeverityScore(cls) + numeric + Math.min(vlmSeverityScore(vlm) / 100, 80);
  if (status === "official-monitor-points") return Math.max(officialSeverityScore(cls) - 2_000, 6_000) + numeric;
  if (status === "external-prediction") return 3_000 + numeric;
  return vlmSeverityScore(vlm) + numeric;
}

function priorityFeatureLabel(feature: DamageFeature, vlm: VlmRecord | undefined, language: Language, status?: string) {
  const p = feature.properties;
  const official = String(p.damage_class ?? p.damage_gra ?? p.confirmed_damage_class ?? "candidate");
  const vlmClass = vlm?.vlm?.damage_class;
  if (status === "external-prediction") {
    return language === "es" ? `Predicción externa: ${official} · solo triage` : `External prediction: ${official} · triage only`;
  }
  if (status === "official-monitor-points") {
    return language === "es" ? `MONIT01 oficial: ${official}` : `Official MONIT01: ${official}`;
  }
  if (status === "official-vector") {
    if (vlmClass) {
      return language === "es" ? `EMS oficial: ${official} · VLM: ${vlmClass}` : `Official EMS: ${official} · VLM: ${vlmClass}`;
    }
    return language === "es" ? `EMS oficial: ${official}` : `Official EMS: ${official}`;
  }
  return String(vlmClass ?? official);
}

type DownloadGroupId = "field" | "gis" | "evidence" | "imagery" | "other";
type DownloadItem = {
  kind: string;
  href: string;
  label: string;
};
type DownloadGroup = {
  id: DownloadGroupId;
  title: string;
  items: DownloadItem[];
};

function downloadGroupId(kind: string): DownloadGroupId {
  const normalized = kind.toLowerCase();
  if (normalized === "csv" || normalized === "kml") return "field";
  if (normalized === "geojson" || normalized === "shp" || normalized === "gdb") return "gis";
  if (normalized.startsWith("vlm")) return "evidence";
  if (normalized === "cog" || normalized === "tif" || normalized === "tiff" || normalized === "pdf" || normalized === "xls" || normalized === "xlsx" || normalized === "web") return "imagery";
  return "other";
}

function downloadLabel(kind: string, language: Language) {
  const normalized = kind.toLowerCase();
  const labels: Record<string, string> = {
    csv: "CSV",
    geojson: "GeoJSON",
    kml: "KML",
    cog: "COG",
    shp: "SHP",
    gdb: "GDB",
    xls: "XLS",
    xlsx: "XLSX",
    web: "WEB",
    vlm_jsonl: "VLM JSONL",
    vlm_csv: "VLM CSV",
    vlm_summary: language === "es" ? "Resumen VLM" : "VLM summary",
    vlm_before_after_jsonl: language === "es" ? "Antes/desp. JSONL" : "Before/after JSONL",
    vlm_before_after_csv: language === "es" ? "Antes/desp. CSV" : "Before/after CSV",
    vlm_before_after_summary: language === "es" ? "Resumen A/D" : "B/A summary",
  };
  return labels[normalized] ?? kind.toUpperCase().replaceAll("_", " ");
}

function buildDownloadGroups(downloads: Record<string, string> | undefined, language: Language): DownloadGroup[] {
  const t = copy[language];
  const groups: Record<DownloadGroupId, DownloadGroup> = {
    field: { id: "field", title: t.downloadField, items: [] },
    gis: { id: "gis", title: t.downloadGis, items: [] },
    evidence: { id: "evidence", title: t.downloadEvidence, items: [] },
    imagery: { id: "imagery", title: t.downloadImagery, items: [] },
    other: { id: "other", title: t.downloadOther, items: [] },
  };
  Object.entries(downloads ?? {}).forEach(([kind, href]) => {
    const id = downloadGroupId(kind);
    groups[id].items.push({ kind, href, label: downloadLabel(kind, language) });
  });
  return (["field", "gis", "evidence", "imagery", "other"] as DownloadGroupId[])
    .map((id) => groups[id])
    .filter((group) => group.items.length > 0);
}

function operationalGuidance(aoi: AoiRecord, language: Language) {
  const t = copy[language];
  if (aoi.status === "external-prediction") return t.externalBrief;
  if (aoi.status === "imagery-only") return t.imageryBrief;
  if (aoi.status === "official-monitor-points") return t.monitorBrief;
  return t.officialBrief;
}

function directRasterIsMobileSafe(bytes?: number | null) {
  return !bytes || bytes <= DIRECT_RASTER_MOBILE_MAX_BYTES;
}

function googleMapsUrl(properties: DamageFeature["properties"]) {
  if (typeof properties.google_maps_url === "string" && properties.google_maps_url) return properties.google_maps_url;
  const lat = Number(properties.centroid_lat);
  const lon = Number(properties.centroid_lon);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return "";
  return `https://www.google.com/maps/search/?api=1&query=${lat},${lon}`;
}

function hasNativeBeforeLayer(aoi: AoiRecord | null | undefined) {
  if (!aoi) return false;
  return Boolean(aoi.layers.beforeTiles || (aoi.layers.beforeImage && directRasterIsMobileSafe(aoi.imagery?.before?.bytes)));
}

function hasAfterLayer(aoi: AoiRecord | null | undefined) {
  if (!aoi) return false;
  return Boolean(aoi.layers.afterTiles || (aoi.layers.afterImage && directRasterIsMobileSafe(aoi.imagery?.after?.bytes)));
}

export default function OperationsConsole() {
  const [catalog, setCatalog] = useState<AoiCatalog | null>(null);
  const [catalogStatus, setCatalogStatus] = useState<LoadStatus>("loading");
  const [aoiLayerState, setAoiLayerState] = useState<Record<string, AoiLayerState>>({});
  const [activeId, setActiveId] = useState("emsr884-aoi12-caraballeda");
  const [language, setLanguage] = useState<Language>("es");
  const [filter, setFilter] = useState<Filter>("all");
  const [mode, setMode] = useState<Mode>("after");
  const [basemap, setBasemap] = useState<Basemap>("aerial");
  const [opacity, setOpacity] = useState(52);
  const [selected, setSelected] = useState<DamageFeature | null>(null);
  const [mapControlsOpen, setMapControlsOpen] = useState(false);
  const [isMobileLayout, setIsMobileLayout] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [focusToken, setFocusToken] = useState(0);
  const [aoiFocusToken, setAoiFocusToken] = useState(0);
  const [vlm, setVlm] = useState<Record<string, VlmRecord>>({});
  const [features, setFeatures] = useState<DamageFeature[]>([]);
  const rightRailRef = useRef<HTMLElement | null>(null);
  const desktopPriorityRef = useRef<HTMLElement | null>(null);
  const mobilePriorityRef = useRef<HTMLElement | null>(null);
  const appLoadTrackedRef = useRef(false);
  const sessionStartedAtRef = useRef<number>(0);
  const firstInteractionTrackedRef = useRef(false);
  const loadedDamageAoisRef = useRef<Set<string>>(new Set());
  const loadedVlmAoisRef = useRef<Set<string>>(new Set());
  const mapReadyTrackedRef = useRef<Set<string>>(new Set());
  const firstTileTrackedRef = useRef<Set<string>>(new Set());

  const setLayerStatus = useCallback((aoiId: string, key: keyof AoiLayerState, status: LoadStatus) => {
    setAoiLayerState((current) => ({
      ...current,
      [aoiId]: {
        ...current[aoiId],
        [key]: status,
      },
    }));
  }, []);

  useEffect(() => {
    const viewportQuery = window.matchMedia("(max-width: 760px)");
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncViewport = () => {
      const isMobile = viewportQuery.matches;
      setIsMobileLayout(isMobile);
      if (!isMobile) setInspectorOpen(false);
    };
    const syncMotion = () => setPrefersReducedMotion(motionQuery.matches);
    syncViewport();
    syncMotion();
    viewportQuery.addEventListener("change", syncViewport);
    motionQuery.addEventListener("change", syncMotion);
    return () => {
      viewportQuery.removeEventListener("change", syncViewport);
      motionQuery.removeEventListener("change", syncMotion);
    };
  }, []);

  useEffect(() => {
    fetch("/data/catalog.json")
      .then((r) => {
        if (!r.ok) throw new Error("Unable to load AOI catalog");
        return r.json();
      })
      .then((data) => {
        setCatalog(data);
        setCatalogStatus("ready");
      })
      .catch(() => {
        setCatalogStatus("error");
      });
  }, []);

  useEffect(() => {
    sessionStartedAtRef.current = interactionClockMs();
  }, []);

  const active = useMemo<AoiRecord | undefined>(() => catalog?.aois.find((a) => a.id === activeId), [catalog, activeId]);

  useEffect(() => {
    if (!catalog) return;
    const aoi = catalog.aois.find((candidate) => candidate.id === activeId);
    if (!aoi) return;
    if (!aoi.layers.vlm || loadedVlmAoisRef.current.has(aoi.id)) return;
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) setLayerStatus(aoi.id, "vlm", "loading");
    });
    fetch(aoi.layers.vlm)
      .then((r) => {
        if (!r.ok) throw new Error(`Unable to load VLM data for ${aoi.id}`);
        return r.text();
      })
      .then((text) => {
        if (cancelled) return;
        const entries = text.split("\n").filter(Boolean).map((line) => {
          const entry = JSON.parse(line) as VlmRecord;
          return [`${aoi.id}__${entry.id}`, entry] as const;
        });
        setVlm((current) => ({ ...current, ...Object.fromEntries(entries) }));
        loadedVlmAoisRef.current.add(aoi.id);
        setLayerStatus(aoi.id, "vlm", "ready");
      })
      .catch(() => {
        loadedVlmAoisRef.current.delete(aoi.id);
        if (!cancelled) setLayerStatus(aoi.id, "vlm", "error");
      });
    return () => { cancelled = true; };
  }, [activeId, catalog, setLayerStatus]);

  useEffect(() => {
    if (!catalog) return;
    const aoi = catalog.aois.find((candidate) => candidate.id === activeId);
    if (!aoi) return;
    if (loadedDamageAoisRef.current.has(aoi.id)) return;
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) setLayerStatus(aoi.id, "damage", "loading");
    });
    fetch(aoi.layers.damage)
      .then((r) => {
        if (!r.ok) throw new Error(`Unable to load damage data for ${aoi.id}`);
        return r.json();
      })
      .then((data: { features: DamageFeature[] }) => {
        if (cancelled) return;
        const nextFeatures = (data.features ?? []).map((feature) => {
          const sourceId = String(feature.properties.id);
          return {
            ...feature,
            properties: {
              ...feature.properties,
              id: `${aoi.id}__${sourceId}`,
              source_feature_id: sourceId,
              aoi_id: aoi.id,
              aoi_label_en: aoi.name.en,
              aoi_label_es: aoi.name.es,
            },
          } as DamageFeature;
        });
        setFeatures((current) => {
          const withoutAoi = current.filter((feature) => feature.properties.aoi_id !== aoi.id);
          return [...withoutAoi, ...nextFeatures];
        });
        loadedDamageAoisRef.current.add(aoi.id);
        setLayerStatus(aoi.id, "damage", "ready");
      })
      .catch(() => {
        loadedDamageAoisRef.current.delete(aoi.id);
        if (!cancelled) setLayerStatus(aoi.id, "damage", "error");
      });
    return () => { cancelled = true; };
  }, [activeId, catalog, setLayerStatus]);

  const t = copy[language];
  const metrics = active?.metrics;
  const hasApproximateBefore = Boolean(active?.imagery?.approximateReference?.urlTemplate);
  const hasNativeBeforeImagery = hasNativeBeforeLayer(active);
  const hasBeforeImagery = hasNativeBeforeImagery || hasApproximateBefore;
  const hasAfterImagery = hasAfterLayer(active);
  const hasImagery = hasBeforeImagery || hasAfterImagery;
  const isDemo = active?.status === "test-fixture";
  const isExternalPrediction = active?.status === "external-prediction";
  const statusLabel = (status: string) => t.statuses[status as keyof typeof t.statuses] ?? status;
  const currentLayerState = aoiLayerState[activeId] ?? {};
  const statusMessages = [
    catalogStatus === "loading" ? t.loadingCatalog : undefined,
    catalogStatus === "error" ? t.catalogError : undefined,
    currentLayerState.damage === "loading" ? t.loadingDamage : undefined,
    currentLayerState.damage === "error" ? t.damageError : undefined,
    currentLayerState.vlm === "loading" ? t.loadingVlm : undefined,
    currentLayerState.vlm === "error" ? t.vlmError : undefined,
  ].filter(Boolean) as string[];
  const hasLayerError = currentLayerState.damage === "error" || currentLayerState.vlm === "error" || catalogStatus === "error";
  const cityNavItems = useMemo<CityNavItem[]>(() => {
    if (!catalog) return [];
    const byId = new Map(catalog.aois.map((aoi) => [aoi.id, aoi]));
    return cityGroups.map((group) => {
      const records = group.sourceIds.map((id) => byId.get(id)).filter(Boolean) as AoiRecord[];
      return {
        ...group,
        ...cityResponseScore(records),
      };
    }).sort((a, b) => b.score - a.score || a.name[language].localeCompare(b.name[language]));
  }, [catalog, language]);

  useEffect(() => {
    if (!catalog || appLoadTrackedRef.current || appLoadedTracked) return;
    appLoadTrackedRef.current = true;
    appLoadedTracked = true;
    trackAnalytics("app_loaded", {
      language,
      default_aoi_id: activeId,
      aoi_count: catalog.aois.length,
      default_basemap: basemap,
      default_mode: mode,
      public_static: true,
    });
  }, [activeId, basemap, catalog, language, mode]);

  const trackFirstInteraction = (surface: string) => {
    if (firstInteractionTrackedRef.current) return;
    firstInteractionTrackedRef.current = true;
    const startedAt = sessionStartedAtRef.current;
    trackAnalytics("first_interaction_seconds", {
      seconds: startedAt ? Math.round((interactionClockMs() - startedAt) / 1000) : 0,
      surface,
      aoi_id: activeId,
      language,
    });
  };

  const changeLanguage = (nextLanguage: Language) => {
    trackFirstInteraction("language");
    if (nextLanguage !== language) {
      trackAnalytics("language_switched", {
        from_language: language,
        to_language: nextLanguage,
        aoi_id: activeId,
      });
    }
    setLanguage(nextLanguage);
  };
  const selectAoi = (id: string, cityId?: string) => {
    trackFirstInteraction("aoi");
    if (id !== activeId) {
      const nextAoi = catalog?.aois.find((aoi) => aoi.id === id);
      trackAnalytics("aoi_selected", {
        aoi_id: id,
        city_id: cityId,
        aoi_status: nextAoi?.status,
        language,
      });
    }
    setActiveId(id);
    setAoiLayerState((current) => ({
      ...current,
      [id]: {
        damage: loadedDamageAoisRef.current.has(id) ? "ready" : "idle",
        vlm: loadedVlmAoisRef.current.has(id) ? "ready" : "idle",
      },
    }));
    setSelected(null);
    setMapControlsOpen(false);
    setInspectorOpen(false);
    setFocusToken((value) => value + 1);
    setAoiFocusToken((value) => value + 1);
  };
  const changeMode = (nextMode: Mode) => {
    trackFirstInteraction("imagery_mode");
    if (nextMode !== mode) {
      trackAnalytics("imagery_mode_changed", {
        aoi_id: activeId,
        mode: nextMode,
        has_before_imagery: hasBeforeImagery,
        has_after_imagery: hasAfterImagery,
      });
    }
    setMode(nextMode);
  };
  const changeBasemap = (nextBasemap: Basemap) => {
    trackFirstInteraction("basemap");
    if (nextBasemap !== basemap) {
      trackAnalytics("basemap_changed", {
        aoi_id: activeId,
        basemap: nextBasemap,
      });
    }
    setBasemap(nextBasemap);
  };
  const changeFilter = (nextFilter: Filter) => {
    trackFirstInteraction("filter");
    if (nextFilter !== filter) {
      trackAnalytics("damage_filter_changed", {
        aoi_id: activeId,
        filter: nextFilter,
      });
    }
    setFilter(nextFilter);
  };
  const selectPriorityFeature = (feature: DamageFeature, rank: number) => {
    trackFirstInteraction("priority");
    const p = feature.properties;
    const record = vlm[p.id];
    trackAnalytics("priority_item_clicked", {
      aoi_id: String(p.aoi_id ?? activeId),
      rank,
      damage_class: String(record?.vlm?.damage_class ?? p.damage_class ?? p.damage_gra ?? "unknown"),
      has_vlm: Boolean(record),
      vlm_review_type: record?.vlm?.review_type ?? record?.review_type,
    });
    setSelected(feature);
    setFilter("all");
    setMapControlsOpen(false);
    setInspectorOpen(false);
    setFocusToken((value) => value + 1);
    rightRailRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };
  const scrollToPriority = () => {
    setInspectorOpen(true);
    requestAnimationFrame(() => {
      const target = isSmallViewport() ? mobilePriorityRef.current : desktopPriorityRef.current;
      target?.scrollIntoView({ behavior: prefersReducedMotion ? "auto" : "smooth", block: "start" });
    });
  };
  const adjustOpacity = (delta: number) => setOpacity((value) => Math.max(5, Math.min(90, value + delta)));
  const priorityFeatures = useMemo(() => {
    return features
      .filter((feature) => feature.properties.aoi_id === activeId)
      .sort((a, b) => (
        priorityFeatureScore(b, vlm[b.properties.id], active?.status) -
        priorityFeatureScore(a, vlm[a.properties.id], active?.status)
      ) || String(a.properties.source_feature_id ?? a.properties.id).localeCompare(String(b.properties.source_feature_id ?? b.properties.id)))
      .slice(0, 12);
  }, [active?.status, activeId, features, vlm]);
  const controlSummary = `${basemap === "aerial" ? t.aerialBase : t.mapBase} · ${mode === "after" ? t.after : t.before} · ${opacity}%`;
  const prioritySummary = priorityFeatures.length ? `${priorityFeatures.length} ${t.priorityReady}` : t.noPriorityReady;
  const selectedSummary = selected
    ? String(selected.properties.source_feature_id ?? selected.properties.id)
    : prioritySummary;
  const priorityTitle = language === "es" ? "Prioridad" : "Priority";
  const renderInspectorBody = (bodyId: string, prioritySectionRef: RefObject<HTMLElement | null>) => (
    <div className="inspector-body" id={bodyId}>
      {active && !selected && (
        <OperationalBrief
          aoi={active}
          language={language}
          priorityCount={priorityFeatures.length}
          onReviewPriority={scrollToPriority}
        />
      )}
      <Card className="ops-card evidence-panel" size="sm">
        <CardHeader>
          <CardTitle>{t.evidence}</CardTitle>
        </CardHeader>
        <CardContent>
          {selected ? (
            <Evidence feature={selected} vlm={vlm[selected.properties.id]} language={language} onBackToPriority={scrollToPriority} />
          ) : (
            <p className="muted">{t.noSelection}</p>
          )}
        </CardContent>
      </Card>
      <Card className="ops-card priority-panel" ref={prioritySectionRef as RefObject<HTMLDivElement | null>} size="sm">
        <CardHeader>
          <CardTitle>{priorityTitle}</CardTitle>
          <CardAction>
            <Badge variant="outline">{priorityFeatures.length}</Badge>
          </CardAction>
        </CardHeader>
        <CardContent className="priority-list">
          {priorityFeatures.length === 0 && (
            <p className="muted">
              {currentLayerState.damage === "error"
                ? t.damageError
                : currentLayerState.damage === "loading"
                  ? t.loadingDamage
                  : language === "es" ? "Sin filas de prioridad para este AOI." : "No priority rows for this AOI."}
            </p>
          )}
          {priorityFeatures.map((feature, index) => {
            const p = feature.properties;
            const label = priorityFeatureLabel(feature, vlm[p.id], language, active?.status);
            return (
              <Button key={p.id} variant="outline" data-testid={`priority-${p.source_feature_id ?? p.id}`} aria-pressed={selected?.properties.id === p.id} className={selected?.properties.id === p.id ? "priority-row active" : "priority-row"} onClick={() => selectPriorityFeature(feature, index + 1)}>
                <b>{p.source_feature_id ?? p.id}</b>
                <span>{label} · {String(p.damage_score ?? p.damage_percent ?? "-")}</span>
              </Button>
            );
          })}
        </CardContent>
      </Card>
      {active?.imagery && (
        <ImageryCoveragePanel
          aoi={active}
          language={language}
          hasAfterLayer={hasAfterImagery}
          hasBeforeLayer={hasNativeBeforeImagery}
          hasNativeBeforeLayer={hasNativeBeforeImagery}
        />
      )}
      <Card className="ops-card confidence-panel" size="sm">
        <CardHeader>
          <CardTitle>{t.confidenceTitle}</CardTitle>
        </CardHeader>
        <CardContent>
          <p>{t.confidenceText}</p>
        </CardContent>
      </Card>
      {active && <VlmQualityPanel aoi={active} language={language} />}
      <Card className="ops-card watch-panel" size="sm">
        <CardHeader>
          <CardTitle>{t.watchlist}</CardTitle>
        </CardHeader>
        <CardContent>
          {catalog?.watchlist.map((item) => (
            <div className="watch-row" key={item.id}>
              <b>{item.name[language]}</b>
              <span>{statusLabel(item.status)} · {item.expectedUtc}</span>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card className="ops-card architecture" size="sm">
        <CardHeader>
          <CardTitle>{t.architecture}</CardTitle>
        </CardHeader>
        <CardContent>
          <p>{t.architectureText}</p>
        </CardContent>
      </Card>
    </div>
  );

  return (
    <main className="ops-shell">
      <aside className="left-rail">
        <div className="brand-block">
          <div className="status-pill">{t.live}</div>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
          <p className="quick-start">{t.quickStart}</p>
        </div>

        <label className="field-label">{t.language}</label>
        <div className="segmented" aria-label={t.language}>
          <Button variant={language === "es" ? "default" : "outline"} className={language === "es" ? "active" : ""} aria-pressed={language === "es"} onClick={() => changeLanguage("es")}>ES</Button>
          <Button variant={language === "en" ? "default" : "outline"} className={language === "en" ? "active" : ""} aria-pressed={language === "en"} onClick={() => changeLanguage("en")}>EN</Button>
        </div>

        <label className="field-label">{t.aoi}</label>
        <div className="aoi-list">
          {cityNavItems.map((item) => (
            <Button key={item.id} variant="outline" data-testid={`city-${item.id}`} aria-pressed={item.sourceIds.includes(activeId)} className={item.sourceIds.includes(activeId) ? "aoi-card active" : "aoi-card"} onClick={() => selectAoi(item.primaryAoiId, item.id)}>
              <span>{item.name[language]}</span>
              <small>{cityImpactLabel(item, language)}</small>
            </Button>
          ))}
        </div>
        <p className="muted">{t.rankingNote}</p>

        {active && (
          <Card className="ops-card source-card" size="sm">
            <CardHeader>
              <CardTitle>{t.source}</CardTitle>
              <CardAction>
                <Badge variant={(isDemo || isExternalPrediction) ? "secondary" : "default"}>
                  {isDemo ? t.demoOnly : isExternalPrediction ? t.externalPrediction : t.officialData}
                </Badge>
              </CardAction>
            </CardHeader>
            <CardContent>
              <p>{active.source}</p>
              <Separator className="my-2" />
              <div className="meta-row"><span>{t.status}</span><b>{statusLabel(active.status)}</b></div>
            </CardContent>
          </Card>
        )}

        {statusMessages.length > 0 && (
          <Alert className={hasLayerError ? "data-status error" : "data-status"} variant={hasLayerError ? "destructive" : "default"} role="status" aria-live="polite">
            <AlertDescription>
              {statusMessages.map((message) => <p key={message}>{message}</p>)}
            </AlertDescription>
          </Alert>
        )}

        <section className="kpi-grid" aria-label={language === "es" ? "Métricas del AOI" : "AOI metrics"}>
          <div><b>{metrics?.features ?? "-"}</b><span>{t.features}</span></div>
          <div><b>{metrics?.damagedConfirmed ?? 0}</b><span>{t.confirmed}</span></div>
          <div><b>{metrics?.candidates ?? metrics?.possibleDamage ?? 0}</b><span>{t.candidates}</span></div>
          <div>
            <b>{metrics?.vlmBeforeAfterReviewed ?? metrics?.vlmReviewed ?? metrics?.vlmPostEventReviewed ?? 0}</b>
            <span>{metrics?.vlmBeforeAfterReviewed ? t.vlm : metrics?.vlmPostEventReviewed ? t.vlmPostEvent : t.vlm}</span>
          </div>
        </section>

        <section className="downloads-section">
          <h2>{t.downloads}</h2>
          <DownloadGroups downloads={active?.downloads} language={language} aoiId={active?.id} surface="downloads_panel" />
        </section>
      </aside>

      <section className="map-stage">
        {active && (
          <MapPanel
            aoi={active}
            features={features}
            mode={mode}
            opacity={opacity / 100}
            filter={filter}
            basemap={basemap}
            vlm={vlm}
            selectedId={selected?.properties.id}
            focusToken={focusToken}
            aoiFocusToken={aoiFocusToken}
            onMapReady={(payload) => {
              const key = `${payload.aoi_id}:${payload.feature_count}`;
              if (mapReadyTrackedRef.current.has(key)) return;
              mapReadyTrackedRef.current.add(key);
              trackAnalytics("map_ready", payload);
            }}
            onFirstTileLoaded={(payload) => {
              const key = `${payload.aoi_id}:${payload.layer}`;
              if (firstTileTrackedRef.current.has(key)) return;
              firstTileTrackedRef.current.add(key);
              trackAnalytics("first_tile_loaded", payload);
            }}
            onSelect={(feature) => {
              trackFirstInteraction(feature ? "map_feature" : "map_empty");
              setSelected(feature);
              setMapControlsOpen(false);
              setInspectorOpen(false);
            }}
          />
        )}
        <div className={mapControlsOpen ? "map-toolbar open" : "map-toolbar"} data-testid="map-toolbar">
          <Button
            type="button"
            variant="outline"
            className="map-toolbar-toggle"
            data-testid="map-controls-toggle"
            aria-expanded={mapControlsOpen}
            aria-controls="map-toolbar-body"
            onClick={() => setMapControlsOpen((open) => !open)}
          >
            <span>{t.controls}</span>
            <em>{mapControlsOpen ? (language === "es" ? "Cerrar" : "Close") : (language === "es" ? "Abrir" : "Open")}</em>
            <b>{controlSummary}</b>
          </Button>
          <div className="map-toolbar-body" id="map-toolbar-body">
            <div className="control-group">
              <span>{t.basemap}</span>
              <div className="button-row">
                <Button variant={basemap === "map" ? "default" : "outline"} data-testid="basemap-map" aria-pressed={basemap === "map"} className={basemap === "map" ? "active" : ""} onClick={() => changeBasemap("map")}>{t.mapBase}</Button>
                <Button variant={basemap === "aerial" ? "default" : "outline"} data-testid="basemap-aerial" aria-pressed={basemap === "aerial"} className={basemap === "aerial" ? "active" : ""} onClick={() => changeBasemap("aerial")}>{t.aerialBase}</Button>
              </div>
            </div>
            <div className="control-group">
              <span>{t.mode}</span>
              <div className="button-row">
                <Button variant={mode === "before" ? "default" : "outline"} data-testid="mode-before" disabled={!hasBeforeImagery} aria-pressed={mode === "before"} className={mode === "before" ? "active" : ""} onClick={() => changeMode("before")}>{t.before}</Button>
                <Button variant={mode === "after" ? "default" : "outline"} data-testid="mode-after" disabled={!hasAfterImagery} aria-pressed={mode === "after"} className={mode === "after" ? "active" : ""} onClick={() => changeMode("after")}>{t.after}</Button>
              </div>
            </div>
            <label className="range-control">
              <span>{t.opacity} <b>{opacity}%</b></span>
              <div className="range-row">
                <Button type="button" variant="outline" aria-label={language === "es" ? "bajar opacidad de daño" : "reduce damage opacity"} onClick={() => adjustOpacity(-10)}>-</Button>
                <input type="range" min="5" max="90" value={opacity} aria-label={t.opacity} onInput={(e) => setOpacity(Number(e.currentTarget.value))} onChange={(e) => setOpacity(Number(e.currentTarget.value))} />
                <Button type="button" variant="outline" aria-label={language === "es" ? "subir opacidad de daño" : "increase damage opacity"} onClick={() => adjustOpacity(10)}>+</Button>
              </div>
            </label>
            <div className="control-group">
              <span>{t.filters}</span>
              <div className="button-row">
                <Button variant={filter === "all" ? "default" : "outline"} data-testid="filter-all" aria-pressed={filter === "all"} className={filter === "all" ? "active" : ""} onClick={() => changeFilter("all")}>{t.all}</Button>
                <Button variant={filter === "severe" ? "default" : "outline"} data-testid="filter-severe" aria-pressed={filter === "severe"} className={filter === "severe" ? "active" : ""} onClick={() => changeFilter("severe")}>{t.severe}</Button>
                <Button variant={filter === "vlm" ? "default" : "outline"} data-testid="filter-vlm" aria-pressed={filter === "vlm"} className={filter === "vlm" ? "active" : ""} onClick={() => changeFilter("vlm")}>{t.vlmOnly}</Button>
              </div>
            </div>
            <details className="map-toolbar-notes">
              <summary>{language === "es" ? "Notas" : "Notes"}</summary>
              <p>{t.aerialBaseNote}</p>
              {!hasImagery && <p>{t.noImagery}</p>}
              {hasApproximateBefore && !hasNativeBeforeImagery && <p>{t.approximateBefore}</p>}
              {hasAfterImagery && !hasBeforeImagery && <p>{active?.imagery?.before ? t.beforeEvidenceOnly : t.noBefore}</p>}
              <p>{t.filterNote}</p>
            </details>
          </div>
        </div>
      </section>

      {!isMobileLayout && (
        <aside className="right-rail desktop-right-rail" ref={rightRailRef} data-testid="right-rail">
          {renderInspectorBody("desktop-inspector-body", desktopPriorityRef)}
        </aside>
      )}

      {isMobileLayout && (
        <div className={inspectorOpen ? "mobile-sheet-shell open" : "mobile-sheet-shell"} data-testid="right-rail">
          {!inspectorOpen && (
            <Button
              type="button"
              variant="outline"
              className="mobile-sheet-trigger"
              data-testid="mobile-inspector-toggle"
              aria-expanded={inspectorOpen}
              aria-controls="mobile-inspector-body"
              onClick={() => setInspectorOpen(true)}
            >
              <span>{t.evidence} / {priorityTitle}</span>
              <em>{language === "es" ? "Abrir" : "Open"}</em>
              <b>{selectedSummary}</b>
            </Button>
          )}
          <Drawer open={inspectorOpen} onOpenChange={setInspectorOpen} direction="bottom" modal={false}>
            <DrawerContent className="mobile-sheet-container shadcn-mobile-drawer" data-testid="mobile-inspector-sheet" aria-label={`${t.evidence} / ${priorityTitle}`}>
              <DrawerHeader className="mobile-sheet-header">
                <div className="mobile-sheet-handle" aria-hidden="true" />
                <div className="mobile-sheet-titlebar">
                  <div>
                    <DrawerTitle>{t.evidence} / {priorityTitle}</DrawerTitle>
                    <DrawerDescription>{selectedSummary}</DrawerDescription>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={() => setInspectorOpen(false)}>{language === "es" ? "Cerrar" : "Close"}</Button>
                </div>
              </DrawerHeader>
              <ScrollArea className="mobile-sheet-content mobile-sheet-scroller">
                <div className="mobile-sheet-body">
                  {renderInspectorBody("mobile-inspector-body", mobilePriorityRef)}
                </div>
              </ScrollArea>
            </DrawerContent>
          </Drawer>
        </div>
      )}
    </main>
  );
}

function OperationalBrief({
  aoi,
  language,
  priorityCount,
  onReviewPriority,
}: {
  aoi: AoiRecord;
  language: Language;
  priorityCount: number;
  onReviewPriority: () => void;
}) {
  const t = copy[language];
  const fieldDownloads = buildDownloadGroups(aoi.downloads, language).find((group) => group.id === "field")?.items ?? [];
  const confirmed = n(aoi.metrics.damagedConfirmed);
  const possible = n(aoi.metrics.possibleDamage);
  const vlmActionable = n(aoi.metrics.vlmBeforeAfterActionable ?? aoi.metrics.vlmPostEventUrgentReview);
  const hasOfficialDamage = confirmed > 0 || possible > 0;
  const sourceLabel = aoi.status === "external-prediction"
    ? t.externalPrediction
    : aoi.status === "imagery-only"
      ? t.imageryOnly
      : aoi.status === "official-monitor-points"
        ? t.statuses["official-monitor-points"]
        : t.officialData;

  return (
    <Card className="ops-card operational-brief" size="sm">
      <CardHeader>
        <CardTitle role="heading" aria-level={2}>{t.operationalBrief}</CardTitle>
        <CardAction>
          <Badge variant="secondary">{sourceLabel}</Badge>
        </CardAction>
      </CardHeader>
      <CardContent>
        <div className="brief-callout">
          <small>{t.recommendedAction}</small>
          <p>{operationalGuidance(aoi, language)}</p>
        </div>
        <div className="brief-facts">
          <div><b>{hasOfficialDamage ? confirmed : n(aoi.metrics.features)}</b><span>{hasOfficialDamage ? t.confirmed : t.features}</span></div>
          <div><b>{possible}</b><span>{t.possible}</span></div>
          <div><b>{priorityCount}</b><span>{t.priorityReady}</span></div>
          <div><b>{vlmActionable}</b><span>{t.vlmActionable}</span></div>
        </div>
      </CardContent>
      <CardContent className="brief-actions">
        <Button type="button" className="text-action primary-action" onClick={onReviewPriority}>{t.reviewPriority}</Button>
        {fieldDownloads.slice(0, 2).map((item) => (
          <a
            key={item.kind}
            className={cn(buttonVariants({ variant: "outline" }), "text-action")}
            href={item.href}
            data-analytics-event="data_download_clicked"
            data-analytics-aoi={aoi.id}
            data-analytics-format={item.kind.toLowerCase()}
            data-analytics-surface="operational_brief"
          >
            {item.label}
          </a>
        ))}
      </CardContent>
      <CardContent>
        <p className="muted brief-hint">{t.lightModeHint}</p>
      </CardContent>
    </Card>
  );
}

function DownloadGroups({
  downloads,
  language,
  aoiId,
  surface,
}: {
  downloads?: Record<string, string>;
  language: Language;
  aoiId?: string;
  surface: string;
}) {
  const groups = buildDownloadGroups(downloads, language);
  if (groups.length === 0) {
    return <p className="muted">{language === "es" ? "Sin descargas publicadas para este AOI." : "No downloads published for this AOI."}</p>;
  }
  return (
    <div className="download-groups">
      {groups.map((group) => (
        <div className="download-group" key={group.id}>
          <div className="download-group-title">
            <span>{group.title}</span>
          </div>
          <div className="download-row">
            {group.items.map((item) => (
              <a
                key={item.kind}
                className={cn(buttonVariants({ variant: "outline", size: "sm" }), "download-link")}
                href={item.href}
                data-analytics-event="data_download_clicked"
                data-analytics-aoi={aoiId}
                data-analytics-format={item.kind.toLowerCase()}
                data-analytics-surface={surface}
              >
                {item.label}
              </a>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ImageryCoveragePanel({
  aoi,
  language,
  hasAfterLayer,
  hasBeforeLayer,
  hasNativeBeforeLayer,
}: {
  aoi: AoiRecord;
  language: Language;
  hasAfterLayer: boolean;
  hasBeforeLayer: boolean;
  hasNativeBeforeLayer: boolean;
}) {
  const t = copy[language];
  const afterStatus = aoi.imagery?.after
    ? `${hasAfterLayer ? t.mapLayerAvailable : t.evidenceOnly} · ${t.officialAfter}`
    : t.notAvailable;
  const beforeStatus = aoi.imagery?.before
    ? `${hasBeforeLayer ? t.mapLayerAvailable : t.evidenceOnly} · ${t.nonOfficialBefore}`
    : aoi.imagery?.approximateReference
      ? `${t.mapLayerAvailable} · ${aoi.imagery.approximateReference.label}`
    : t.notAvailable;
  const hasCogDownload = Boolean(aoi.imagery?.after?.url);

  return (
    <section className="imagery-panel">
      <h2>{t.imageryCoverage}</h2>
      <dl>
        <div><dt>AOI</dt><dd>{aoi.id}</dd></div>
        <div><dt>{t.afterImagery}</dt><dd>{afterStatus}</dd></div>
        {aoi.imagery?.after && (
          <>
            <div><dt>Sensor</dt><dd>{aoi.imagery.after.sensor ?? "-"}</dd></div>
            <div><dt>UTC</dt><dd>{aoi.imagery.after.acquisitionUtc ?? "-"}</dd></div>
            <div><dt>Size</dt><dd>{formatBytes(aoi.imagery.after.bytes)}</dd></div>
          </>
        )}
        <div><dt>{t.beforeImagery}</dt><dd>{beforeStatus}</dd></div>
      {aoi.imagery?.before?.coverage && <div><dt>{t.coverage}</dt><dd>{aoi.imagery.before.coverage}</dd></div>}
      </dl>
      {aoi.imagery?.approximateReference && !hasNativeBeforeLayer && (
        <p className="muted imagery-note">{aoi.imagery.approximateReference.limitations}</p>
      )}
      {!aoi.metrics.features && <p className="muted">{t.imageryOnly}</p>}
      {aoi.imagery?.note && <p className="muted imagery-note">{aoi.imagery.note}</p>}
      {hasCogDownload && (
        <div className="download-row">
          <a
            href={aoi.imagery?.after?.url}
            target="_blank"
            rel="noreferrer"
            data-analytics-event="data_download_clicked"
            data-analytics-aoi={aoi.id}
            data-analytics-format="cog"
            data-analytics-surface="imagery_panel"
          >
            COG
          </a>
        </div>
      )}
    </section>
  );
}

function formatBytes(bytes?: number) {
  if (!bytes) return "-";
  if (bytes > 1_000_000_000) return `${(bytes / 1_000_000_000).toFixed(2)} GB`;
  return `${Math.round(bytes / 1_000_000)} MB`;
}

function VlmQualityPanel({ aoi, language }: { aoi: AoiRecord; language: Language }) {
  const t = copy[language];
  const metrics = aoi.metrics;
  const reviewed = metrics.vlmBeforeAfterReviewed ?? 0;
  const skipped = metrics.vlmBeforeAfterSkippedNoBefore ?? 0;
  const uncertain = metrics.vlmBeforeAfterUncertain ?? 0;
  const actionable = metrics.vlmBeforeAfterActionable ?? 0;
  const urgent = metrics.vlmBeforeAfterUrgentReview ?? 0;
  if (!reviewed && !skipped) return null;
  const totalAttempted = reviewed + skipped;
  const uncertaintyRate = reviewed ? Math.round((uncertain / reviewed) * 100) : 0;
  const coverageRate = totalAttempted ? Math.round((reviewed / totalAttempted) * 100) : 0;
  return (
    <section className="vlm-quality-panel">
      <h2>{t.vlmQualityTitle}</h2>
      <div className="mini-metrics">
        <div><b>{reviewed}</b><span>{t.vlmCoverage}</span></div>
        <div><b>{skipped}</b><span>{t.vlmSkipped}</span></div>
        <div><b>{uncertain}</b><span>{t.vlmUncertain} · {uncertaintyRate}%</span></div>
        <div><b>{actionable}</b><span>{t.vlmActionable}</span></div>
        <div><b>{urgent}</b><span>{t.vlmUrgent}</span></div>
        <div><b>{coverageRate}%</b><span>{language === "es" ? "cobertura útil" : "usable coverage"}</span></div>
      </div>
      <p>{t.vlmQualityNote}</p>
    </section>
  );
}

function Evidence({ feature, vlm, language, onBackToPriority }: { feature: DamageFeature; vlm?: VlmRecord; language: Language; onBackToPriority: () => void }) {
  const t = copy[language];
  const p = feature.properties;
  const chip = evidenceChip(vlm);
  const mapsUrl = googleMapsUrl(p);
  const aoiId = String(p.aoi_id ?? "");
  const hasVlm = Boolean(vlm);
  return (
    <div className="evidence-body">
      <h3>{p.source_feature_id ?? p.id}</h3>
      <dl>
        <div><dt>AOI</dt><dd>{language === "es" ? p.aoi_label_es : p.aoi_label_en}</dd></div>
        <div><dt>Pixel</dt><dd>{p.damage_class ?? p.damage_gra ?? p.confirmed_damage_class ?? "unknown"}</dd></div>
        <div><dt>Score</dt><dd>{p.damage_score ?? p.damage_percent ?? p.confirmed_damage_percent ?? "-"}</dd></div>
        <div><dt>VLM</dt><dd>{vlm?.vlm?.damage_class ?? "not reviewed"}</dd></div>
        <div><dt>VLM type</dt><dd>{vlm ? (vlm.vlm?.review_type ?? vlm.review_type ?? "post_event_only") : "-"}</dd></div>
        <div><dt>Priority</dt><dd>{vlm?.vlm?.action_priority ?? "-"}</dd></div>
      </dl>
      {vlm?.vlm?.change_evidence && <p className="evidence-text">{vlm.vlm.change_evidence}</p>}
      {vlm?.vlm?.evidence && <p className="evidence-text">{vlm.vlm.evidence}</p>}
      {vlm?.vlm?.uncertainty_reason && <p className="evidence-text"><b>Uncertainty:</b> {vlm.vlm.uncertainty_reason}</p>}
      {chip && <a
        href={chip.url}
        target="_blank"
        rel="noreferrer"
        data-analytics-event="evidence_chip_clicked"
        data-analytics-aoi={aoiId}
        data-analytics-chip-kind={chip.kind}
        data-analytics-surface="evidence_preview"
        data-analytics-has-vlm={String(hasVlm)}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          className="chip-preview"
          src={chip.url}
          alt={language === "es" ? "Chip de evidencia del elemento seleccionado" : "Evidence chip for selected feature"}
          loading="lazy"
        />
      </a>}
      <div className="download-row">
        {mapsUrl && <a
          href={mapsUrl}
          target="_blank"
          rel="noreferrer"
          data-analytics-event="google_maps_link_clicked"
          data-analytics-aoi={aoiId}
          data-analytics-surface="evidence_panel"
          data-analytics-has-vlm={String(hasVlm)}
        >
          {t.maps}
        </a>}
        {chip && <a
          href={chip.url}
          target="_blank"
          rel="noreferrer"
          data-analytics-event="evidence_chip_clicked"
          data-analytics-aoi={aoiId}
          data-analytics-chip-kind={chip.kind}
          data-analytics-surface="evidence_button"
          data-analytics-has-vlm={String(hasVlm)}
        >
          {t.chip}
        </a>}
        <button type="button" className="text-action" onClick={onBackToPriority}>{t.backToPriority}</button>
      </div>
    </div>
  );
}

function evidenceChip(vlm?: VlmRecord) {
  const entries = [
    ["compare", vlm?.compare_chip],
    ["post_event", vlm?.post_event_chip],
    ["before_event", vlm?.before_event_chip],
    ["triplet", vlm?.triplet_chip],
  ] as const;
  const match = entries.find(([, value]) => value);
  if (!match?.[1]) return undefined;
  const candidate = match[1];
  const kind = match[0];
  if (candidate.startsWith("http://") || candidate.startsWith("https://") || candidate.startsWith("/data/chips/")) return { url: candidate, kind };
  const marker = "/data/chips/";
  const index = candidate.indexOf(marker);
  if (index >= 0) return { url: candidate.slice(index), kind };
  const bareIndex = candidate.indexOf("chips/");
  if (bareIndex >= 0) return { url: `/data/${candidate.slice(bareIndex)}`, kind };
  return { url: candidate, kind };
}
