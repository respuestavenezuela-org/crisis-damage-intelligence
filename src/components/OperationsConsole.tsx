"use client";

import { type RefObject, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Fuse from "fuse.js";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Drawer, DrawerContent, DrawerDescription, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { trackAnalytics } from "@/lib/analytics";
import { persistLang, readStoredLang } from "@/lib/lang";
import { getOfflineBudgetBytes, precacheAoi } from "@/lib/offline-cache";
import { cn } from "@/lib/utils";
import MapPanel from "./map/MapPanel";
import TranslatorBanner from "./TranslatorBanner";
import type { AoiCatalog, AoiRecord, DamageFeature, Language, VlmRecord } from "./types";

const DIRECT_RASTER_MOBILE_MAX_BYTES = 250_000_000;

type PrioritySort = "default" | "damage" | "vlm" | "official" | "source" | "near";

type SearchResultItem =
  | {
      type: "aoi";
      id: string;
      title: string;
      subtitle: string;
      tokens: string;
      aoiId: string;
      cityId?: string;
    }
  | {
      type: "feature";
      id: string;
      title: string;
      subtitle: string;
      tokens: string;
      featureId: string;
    }
  | {
      type: "download";
      id: string;
      title: string;
      subtitle: string;
      tokens: string;
      href: string;
      kind: string;
    };

function scheduleIdle(cb: () => void) {
  const ric =
    typeof window !== "undefined"
      ? (window as unknown as { requestIdleCallback?: (cb: () => void) => number }).requestIdleCallback
      : undefined;
  if (typeof ric === "function") ric(cb);
  else setTimeout(cb, 1200);
}

const copy = {
  en: {
    title: "Respuesta Venezuela",
    subtitle: "Geospatial damage triage for earthquake response",
    live: "Public read-only",
    language: "Language",
    aoi: "Go to affected area",
    quickStart: "Start with La Guaira · open Priority · tap red structures",
    translatorTitle: "Volunteer translator",
    translatorBody: "Bridge Spanish ↔ English with local rescue teams. Can run on your device.",
    translatorOpen: "Open translator",
    translatorTelegram: "Telegram bot",
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
    search: "Search",
    searchPlaceholder: "Search zone, priority id, damage, download...",
    searchHint: "Search active zone data and published AOIs.",
    searchResults: "Search results",
    noSearchResults: "No matching results in the active data.",
    searchAoi: "Zone",
    searchPriority: "Priority",
    searchDownload: "Download",
    context: "Context",
    copyCoords: "Copy coordinates",
    copied: "Coordinates copied",
    copyFailed: "Could not copy coordinates",
    sortDefault: "Default",
    sortDamage: "Highest damage",
    sortVlm: "With VLM",
    sortOfficial: "Official EMS",
    sortSource: "Source ID",
    sortNear: "Near center",
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
    translatorTitle: "Traductor para voluntarios",
    translatorBody: "Comunícate en español ↔ inglés con los equipos locales. Puede ejecutarse en tu dispositivo.",
    translatorOpen: "Abrir traductor",
    translatorTelegram: "Bot de Telegram",
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
    search: "Buscar",
    searchPlaceholder: "Busca zona, id, daño, descarga...",
    searchHint: "Busca en la zona activa y AOIs publicados.",
    searchResults: "Resultados de búsqueda",
    noSearchResults: "Sin resultados en los datos activos.",
    searchAoi: "Zona",
    searchPriority: "Prioridad",
    searchDownload: "Descarga",
    context: "Contexto",
    copyCoords: "Copiar coordenadas",
    copied: "Coordenadas copiadas",
    copyFailed: "No se pudieron copiar coordenadas",
    sortDefault: "Default",
    sortDamage: "Mayor daño",
    sortVlm: "Con VLM",
    sortOfficial: "Oficial EMS",
    sortSource: "ID fuente",
    sortNear: "Cerca del centro",
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

function featureLatLon(feature: DamageFeature) {
  const lat = Number(feature.properties.centroid_lat);
  const lon = Number(feature.properties.centroid_lon);
  if (Number.isFinite(lat) && Number.isFinite(lon)) return { lat, lon };
  return null;
}

function googleMapsUrlForFeature(feature: DamageFeature) {
  const point = featureLatLon(feature);
  if (!point) return undefined;
  return `https://www.google.com/maps/search/?api=1&query=${point.lat},${point.lon}`;
}

function distanceFromAoiCenter(feature: DamageFeature, aoi?: AoiRecord) {
  const point = featureLatLon(feature);
  if (!point || !aoi) return Number.POSITIVE_INFINITY;
  const [centerLat, centerLon] = aoi.center;
  return (point.lat - centerLat) ** 2 + (point.lon - centerLon) ** 2;
}

function officialRank(feature: DamageFeature, status?: string) {
  if (status === "external-prediction") return 0;
  return feature.properties.not_official_ems ? 0 : 1;
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
  const [language, setLanguage] = useState<Language>(readStoredLang);
  const [filter, setFilter] = useState<Filter>("all");
  const [mode, setMode] = useState<Mode>("after");
  const [basemap, setBasemap] = useState<Basemap>("aerial");
  const [opacity, setOpacity] = useState(52);
  const [selected, setSelected] = useState<DamageFeature | null>(null);
  const [prioritySort, setPrioritySort] = useState<PrioritySort>("default");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchAnnouncement, setSearchAnnouncement] = useState("");
  const [mapControlsOpen, setMapControlsOpen] = useState(false);
  const [isMobileLayout, setIsMobileLayout] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [mobileSheet, setMobileSheet] = useState<"none" | "about" | "zona" | "capas">("none");
  const [offlineStatus, setOfflineStatus] = useState<{ done: number; total: number; ready: boolean }>({ done: 0, total: 0, ready: false });
  const precachedAoisRef = useRef<Set<string>>(new Set());
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
  const returnFocusRef = useRef(false);
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
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    if (!isMobileLayout) return;
    if (inspectorOpen) {
      const raf = requestAnimationFrame(() => {
        (document.querySelector('[data-testid="mobile-inspector-close"]') as HTMLElement | null)?.focus();
      });
      const onKey = (event: KeyboardEvent) => {
        if (event.key === "Escape") setInspectorOpen(false);
      };
      window.addEventListener("keydown", onKey);
      return () => {
        cancelAnimationFrame(raf);
        window.removeEventListener("keydown", onKey);
      };
    }
    if (returnFocusRef.current) {
      returnFocusRef.current = false;
      const raf = requestAnimationFrame(() => {
        (document.querySelector('[data-testid="mobile-inspector-toggle"]') as HTMLElement | null)?.focus();
      });
      return () => cancelAnimationFrame(raf);
    }
  }, [inspectorOpen, isMobileLayout]);

  useEffect(() => {
    if (mobileSheet === "none") return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileSheet("none");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileSheet]);

  useEffect(() => {
    if (!searchOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [searchOpen]);

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
  const activeFeatures = useMemo(
    () => features.filter((feature) => feature.properties.aoi_id === activeId),
    [activeId, features],
  );

  useEffect(() => {
    navigator.storage?.persist?.().catch(() => {});
  }, []);

  useEffect(() => {
    const ready = Boolean(active && precachedAoisRef.current.has(active.id));
    setOfflineStatus({ done: 0, total: 0, ready });
  }, [active]);

  useEffect(() => {
    if (typeof window === "undefined" || !("caches" in window)) return;
    if (!active || activeFeatures.length === 0) return;
    if (precachedAoisRef.current.has(active.id)) {
      setOfflineStatus((status) => ({ ...status, ready: true }));
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    const run = async () => {
      const budgetBytes = await getOfflineBudgetBytes();
      const completed = await precacheAoi(active, activeFeatures, vlm, {
        signal: controller.signal,
        budgetBytes,
        onProgress: (progress) => {
          if (!cancelled) {
            setOfflineStatus((status) => ({
              ...status,
              done: progress.done,
              total: progress.total,
              ready: false,
            }));
          }
        },
      });
      if (!cancelled && !controller.signal.aborted) {
        if (completed) precachedAoisRef.current.add(active.id);
        setOfflineStatus((status) => ({ ...status, ready: completed }));
      }
    };
    scheduleIdle(() => {
      if (!cancelled) void run();
    });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [active, activeFeatures, vlm]);

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
  const statusLabel = useCallback((status: string) => t.statuses[status as keyof typeof t.statuses] ?? status, [t]);
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
    persistLang(nextLanguage);
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
    setMobileSheet("none");
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
    const defaultCompare = (a: DamageFeature, b: DamageFeature) => (
      priorityFeatureScore(b, vlm[b.properties.id], active?.status) -
      priorityFeatureScore(a, vlm[a.properties.id], active?.status)
    ) || String(a.properties.source_feature_id ?? a.properties.id).localeCompare(String(b.properties.source_feature_id ?? b.properties.id));
    return [...activeFeatures]
      .sort((a, b) => {
        if (prioritySort === "damage") {
          const aDamage = officialSeverityScore(String(a.properties.damage_class ?? a.properties.damage_gra ?? "")) + n(a.properties.damage_score ?? a.properties.damage_percent);
          const bDamage = officialSeverityScore(String(b.properties.damage_class ?? b.properties.damage_gra ?? "")) + n(b.properties.damage_score ?? b.properties.damage_percent);
          return (bDamage - aDamage) || defaultCompare(a, b);
        }
        if (prioritySort === "vlm") {
          return (Number(Boolean(vlm[b.properties.id])) - Number(Boolean(vlm[a.properties.id]))) || defaultCompare(a, b);
        }
        if (prioritySort === "official") {
          return (officialRank(b, active?.status) - officialRank(a, active?.status)) || defaultCompare(a, b);
        }
        if (prioritySort === "source") {
          return String(a.properties.source_feature_id ?? a.properties.id).localeCompare(String(b.properties.source_feature_id ?? b.properties.id)) || defaultCompare(a, b);
        }
        if (prioritySort === "near") {
          return (distanceFromAoiCenter(a, active) - distanceFromAoiCenter(b, active)) || defaultCompare(a, b);
        }
        return defaultCompare(a, b);
      })
      .slice(0, 12);
  }, [active, activeFeatures, prioritySort, vlm]);
  const controlSummary = `${basemap === "aerial" ? t.aerialBase : t.mapBase} · ${mode === "after" ? t.after : t.before} · ${opacity}%`;
  const prioritySummary = priorityFeatures.length ? `${priorityFeatures.length} ${t.priorityReady}` : t.noPriorityReady;
  const selectedSummary = selected
    ? String(selected.properties.source_feature_id ?? selected.properties.id)
    : prioritySummary;
  const priorityTitle = language === "es" ? "Prioridad" : "Priority";
  const activeCity = cityNavItems.find((item) => item.sourceIds.includes(activeId));
  const searchItems = useMemo<SearchResultItem[]>(() => {
    const items: SearchResultItem[] = [];
    for (const item of cityNavItems) {
      items.push({
        type: "aoi",
        id: `aoi:${item.id}`,
        title: item.name[language],
        subtitle: cityImpactLabel(item, language),
        tokens: `${item.id} ${item.primaryAoiId} ${item.sourceIds.join(" ")}`,
        aoiId: item.primaryAoiId,
        cityId: item.id,
      });
    }
    for (const aoi of catalog?.aois ?? []) {
      const city = cityNavItems.find((item) => item.sourceIds.includes(aoi.id));
      items.push({
        type: "aoi",
        id: `aoi:${aoi.id}`,
        title: aoi.name[language],
        subtitle: `${aoi.id} · ${statusLabel(aoi.status)}`,
        tokens: [
          aoi.id,
          aoi.name.en,
          aoi.name.es,
          aoi.status,
          statusLabel(aoi.status),
          aoi.source,
          city?.id,
          city?.name.en,
          city?.name.es,
        ].filter(Boolean).join(" "),
        aoiId: aoi.id,
        cityId: city?.id,
      });
    }
    for (const feature of activeFeatures) {
      const p = feature.properties;
      const record = vlm[p.id];
      const sourceId = String(p.source_feature_id ?? p.id);
      const title = `${sourceId}`;
      const subtitle = priorityFeatureLabel(feature, record, language, active?.status);
      items.push({
        type: "feature",
        id: `feature:${p.id}`,
        title,
        subtitle,
        tokens: [
          p.id,
          p.source_feature_id,
          p.damage_class,
          p.damage_gra,
          p.confirmed_damage_class,
          p.damage_score,
          p.damage_percent,
          record?.vlm?.damage_class,
          record?.vlm?.action_priority,
          record?.vlm?.review_type,
          record?.review_type,
          active?.name.en,
          active?.name.es,
        ].filter(Boolean).join(" "),
        featureId: p.id,
      });
    }
    for (const group of buildDownloadGroups(active?.downloads, language)) {
      for (const download of group.items) {
        items.push({
          type: "download",
          id: `download:${download.kind}`,
          title: download.label,
          subtitle: group.title,
          tokens: `${download.kind} ${download.label} ${group.title} ${active?.id ?? ""}`,
          href: download.href,
          kind: download.kind,
        });
      }
    }
    return items;
  }, [active, activeFeatures, catalog, cityNavItems, language, statusLabel, vlm]);
  const searchIndex = useMemo(() => new Fuse(searchItems, {
    keys: ["title", "subtitle", "tokens"],
    includeScore: true,
    ignoreLocation: true,
    threshold: 0.36,
  }), [searchItems]);
  const searchResults = useMemo(() => {
    const q = searchQuery.trim();
    if (!q) return [] as SearchResultItem[];
    return searchIndex.search(q, { limit: 14 }).map((result) => result.item);
  }, [searchIndex, searchQuery]);
  const searchResultAnnouncement = searchQuery.trim()
    ? (language === "es"
      ? `${searchResults.length} resultados para ${searchQuery.trim()}`
      : `${searchResults.length} results for ${searchQuery.trim()}`)
    : "";
  const prioritySortOptions: Array<{ id: PrioritySort; label: string }> = [
    { id: "default", label: t.sortDefault },
    { id: "damage", label: t.sortDamage },
    { id: "vlm", label: t.sortVlm },
    { id: "official", label: t.sortOfficial },
    { id: "source", label: t.sortSource },
    { id: "near", label: t.sortNear },
  ];
  const copyFeatureCoords = async (feature: DamageFeature) => {
    const point = featureLatLon(feature);
    if (!point) return;
    const text = `${point.lat},${point.lon}`;
    try {
      if (!navigator.clipboard) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(text);
      setSearchAnnouncement(t.copied);
    } catch {
      setSearchAnnouncement(t.copyFailed);
    }
  };
  const searchResultTestId = (item: SearchResultItem) => {
    if (item.type === "aoi") return `search-result-${item.aoiId}`;
    if (item.type === "feature") return `search-result-${String(item.featureId).split("__").pop() ?? item.featureId}`;
    return `search-result-download-${item.kind}`;
  };
  const renderSearchPanel = (surface: "desktop" | "mobile") => (
    <section className={`search-panel ${surface === "mobile" ? "mobile-search-panel" : ""}`} data-testid={`${surface}-search-panel`} aria-label={t.search}>
      <label className="search-label" htmlFor={`${surface}-search-input`}>{t.search}</label>
      <div className="search-input-row">
        <input
          id={`${surface}-search-input`}
          data-testid="global-search-input"
          type="search"
          value={searchQuery}
          placeholder={t.searchPlaceholder}
          aria-describedby={`${surface}-search-hint ${surface}-search-status`}
          onFocus={() => setSearchOpen(true)}
          onChange={(event) => {
            setSearchQuery(event.currentTarget.value);
            setSearchOpen(true);
          }}
        />
        {searchQuery && (
          <Button type="button" variant="outline" size="sm" aria-label={language === "es" ? "Limpiar búsqueda" : "Clear search"} onClick={() => { setSearchQuery(""); setSearchOpen(false); }}>
            ×
          </Button>
        )}
      </div>
      <p className="search-hint" id={`${surface}-search-hint`}>{t.searchHint}</p>
      <p className="sr-only" id={`${surface}-search-status`} role="status" aria-live="polite">{[searchResultAnnouncement, searchAnnouncement].filter(Boolean).join(" · ")}</p>
      {searchOpen && searchQuery.trim() && (
        <div className="search-results" data-testid="global-search-results" role="listbox" aria-label={t.searchResults}>
          <div className="search-results-heading">
            <span>{t.searchResults}</span>
            <b>{searchResults.length}</b>
          </div>
          {searchResults.length === 0 ? (
            <p className="muted">{t.noSearchResults}</p>
          ) : (
            <div className="search-result-list">
              {searchResults.map((item) => {
                const typeLabel = item.type === "aoi" ? t.searchAoi : item.type === "feature" ? t.searchPriority : t.searchDownload;
                if (item.type === "download") {
                  return (
                    <a
                      key={item.id}
                      className="search-result-row"
                      href={item.href}
                      data-testid={searchResultTestId(item)}
                      role="option"
                      aria-selected="false"
                      data-analytics-event="data_download_clicked"
                      data-analytics-aoi={active?.id}
                      data-analytics-format={item.kind.toLowerCase()}
                      data-analytics-surface={`search_${surface}`}
                    >
                      <span>{typeLabel}</span>
                      <b>{item.title}</b>
                      <small>{item.subtitle}</small>
                    </a>
                  );
                }
                return (
                  <button
                    key={item.id}
                    type="button"
                    className="search-result-row"
                    data-testid={searchResultTestId(item)}
                    role="option"
                    aria-selected="false"
                    onClick={() => {
                      if (item.type === "aoi") {
                        const id = item.aoiId;
                        setActiveId(id);
                        setAoiLayerState((current) => ({
                          ...current,
                          [id]: {
                            damage: "idle",
                            vlm: "idle",
                          },
                        }));
                        setSelected(null);
                        setMapControlsOpen(false);
                        setInspectorOpen(false);
                        setMobileSheet("none");
                        setFocusToken((value) => value + 1);
                        setAoiFocusToken((value) => value + 1);
                        trackAnalytics("aoi_selected", {
                          aoi_id: id,
                          city_id: item.cityId,
                          surface: "search",
                          language,
                        });
                        setSearchOpen(false);
                        setSearchQuery("");
                        return;
                      }
                      const feature = activeFeatures.find((candidate) => candidate.properties.id === item.featureId);
                      if (!feature) return;
                      setSelected(feature);
                      setFilter("all");
                      setMapControlsOpen(false);
                      setInspectorOpen(false);
                      setFocusToken((value) => value + 1);
                      setSearchOpen(false);
                      setSearchQuery("");
                    }}
                  >
                    <span>{typeLabel}</span>
                    <b>{item.title}</b>
                    <small>{item.subtitle}</small>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
    </section>
  );
  const aoiListNode = (
    <div className="aoi-list">
      {cityNavItems.map((item) => (
        <Button key={item.id} variant="outline" data-testid={`city-${item.id}`} aria-pressed={item.sourceIds.includes(activeId)} className={item.sourceIds.includes(activeId) ? "aoi-card active" : "aoi-card"} onClick={() => selectAoi(item.primaryAoiId, item.id)}>
          <span>{item.name[language]}</span>
          <small>{cityImpactLabel(item, language)}</small>
        </Button>
      ))}
    </div>
  );
  const controlsBodyNode = (
    <>
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
          <input type="range" min="5" max="90" value={opacity} aria-label={t.opacity} onInput={(event) => setOpacity(Number(event.currentTarget.value))} onChange={(event) => setOpacity(Number(event.currentTarget.value))} />
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
    </>
  );
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
            <Evidence feature={selected} vlm={vlm[selected.properties.id]} language={language} onBackToPriority={scrollToPriority} onCopyCoords={copyFeatureCoords} />
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
          <div className="priority-sort" role="group" aria-label={language === "es" ? "Ordenar prioridad" : "Sort priority"} data-testid="priority-sort">
            {prioritySortOptions.map((option) => (
              <Button
                key={option.id}
                type="button"
                variant={prioritySort === option.id ? "default" : "outline"}
                size="sm"
                className={prioritySort === option.id ? "active" : ""}
                aria-pressed={prioritySort === option.id}
                data-testid={option.id === "default" ? "priority-sort-response-value" : option.id === "source" ? "priority-sort-source" : `priority-sort-${option.id}`}
                onClick={() => setPrioritySort(option.id)}
              >
                {option.label}
              </Button>
            ))}
          </div>
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
            const mapsUrl = googleMapsUrlForFeature(feature);
            return (
              <div key={p.id} className={selected?.properties.id === p.id ? "priority-row-shell active" : "priority-row-shell"}>
                <Button variant="outline" data-testid={`priority-${p.source_feature_id ?? p.id}`} aria-pressed={selected?.properties.id === p.id} className="priority-row" onClick={() => selectPriorityFeature(feature, index + 1)}>
                  <b>{p.source_feature_id ?? p.id}</b>
                  <span>{label} · {String(p.damage_score ?? p.damage_percent ?? "-")}</span>
                </Button>
                <div className="priority-actions">
                  <Button type="button" variant="outline" size="sm" onClick={() => void copyFeatureCoords(feature)}>
                    {t.copyCoords}
                  </Button>
                  {mapsUrl && (
                    <a
                      className={cn(buttonVariants({ variant: "outline", size: "sm" }), "priority-map-link")}
                      href={mapsUrl}
                      target="_blank"
                      rel="noreferrer"
                      data-analytics-event="google_maps_link_clicked"
                      data-analytics-aoi={String(p.aoi_id ?? activeId)}
                      data-analytics-surface="priority_row"
                    >
                      {t.maps}
                    </a>
                  )}
                </div>
              </div>
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

  const offlinePct = offlineStatus.total > 0 ? Math.round((offlineStatus.done / offlineStatus.total) * 100) : 0;
  const offlineLabel = offlineStatus.ready
    ? (language === "es"
      ? "Zona guardada sin conexión. Refresca con buena señal para actualizar."
      : "Zone saved offline. Refresh with a good connection to update.")
    : offlineStatus.total > 0
      ? (language === "es" ? `Guardando esta zona… ${offlinePct}%` : `Saving this zone… ${offlinePct}%`)
      : "";
  const offlineState = offlineStatus.ready ? "ready" : "saving";
  const contextNode = active && (
    <div className="context-strip" aria-label={t.context}>
      <span>{activeCity?.name[language] ?? active.name[language]}</span>
      <span>{filter === "all" ? t.all : filter === "severe" ? t.severe : t.vlmOnly}</span>
      <span>{mode === "after" ? t.after : t.before}</span>
      <span>{statusLabel(active.status)}</span>
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
          {isMobileLayout && (
            <Button
              type="button"
              variant="outline"
              className="brand-info"
              data-testid="mobile-about-toggle"
              aria-label={language === "es" ? "Información" : "Info"}
              onClick={() => { setInspectorOpen(false); setMobileSheet("about"); }}
            >
              ⓘ
            </Button>
          )}
        </div>
        {!isMobileLayout && <TranslatorBanner language={language} copy={t} />}
        {!isMobileLayout && offlineLabel && (
          <p className={`offline-line ${offlineState}`}>{offlineLabel}</p>
        )}

        <label className="field-label">{t.language}</label>
        <div className="segmented" aria-label={t.language}>
          <Button variant={language === "es" ? "default" : "outline"} className={language === "es" ? "active" : ""} aria-pressed={language === "es"} onClick={() => changeLanguage("es")}>ES</Button>
          <Button variant={language === "en" ? "default" : "outline"} className={language === "en" ? "active" : ""} aria-pressed={language === "en"} onClick={() => changeLanguage("en")}>EN</Button>
        </div>
        {!isMobileLayout && (
          <>
            {renderSearchPanel("desktop")}
            {contextNode}
          </>
        )}

        {!isMobileLayout && (
          <>
            <label className="field-label">{t.aoi}</label>
            {aoiListNode}
            <p className="muted">{t.rankingNote}</p>
          </>
        )}

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

        {!isMobileLayout && statusMessages.length > 0 && (
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

        {!isMobileLayout && (
          <section className="downloads-section">
            <h2>{t.downloads}</h2>
            <DownloadGroups downloads={active?.downloads} language={language} aoiId={active?.id} surface="downloads_panel" />
          </section>
        )}
      </aside>

      <section className="map-stage">
        {isMobileLayout && <TranslatorBanner language={language} copy={t} />}
        {isMobileLayout && renderSearchPanel("mobile")}
        {isMobileLayout && statusMessages.length > 0 && (
          <Alert className={hasLayerError ? "data-status mobile-data-status error" : "data-status mobile-data-status"} variant={hasLayerError ? "destructive" : "default"} role="status" aria-live="polite">
            <AlertDescription>
              {statusMessages.map((message) => <p key={message}>{message}</p>)}
            </AlertDescription>
          </Alert>
        )}
        {isMobileLayout && offlineLabel && (
          <div className={`offline-chip ${offlineState}`} role="note" aria-live="polite">
            <span className="offline-chip-dot" aria-hidden="true" />
            {offlineLabel}
          </div>
        )}
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
        {!isMobileLayout && (
          <div className={`map-toolbar${mapControlsOpen ? " open" : ""}${inspectorOpen ? " inspecting" : ""}`} data-testid="map-toolbar">
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
              {controlsBodyNode}
            </div>
          </div>
        )}
      </section>

      {!isMobileLayout && (
        <aside className="right-rail desktop-right-rail" ref={rightRailRef} data-testid="right-rail">
          {renderInspectorBody("desktop-inspector-body", desktopPriorityRef)}
        </aside>
      )}

      {isMobileLayout && (
        <>
          <div className="mobile-dock" data-testid="right-rail">
            <Button
              type="button"
              variant="outline"
              className="mobile-dock-btn"
              data-testid="mobile-zona-toggle"
              onClick={() => { setInspectorOpen(false); setMobileSheet("zona"); }}
            >
              <span>{language === "es" ? "Zona" : "Zone"}</span>
              <b>{activeCity?.name[language] ?? "—"}</b>
            </Button>
            <Button
              type="button"
              variant="outline"
              className="mobile-dock-btn"
              data-testid="mobile-capas-toggle"
              onClick={() => { setInspectorOpen(false); setMobileSheet("capas"); }}
            >
              <span>{language === "es" ? "Capas" : "Layers"}</span>
              <b>{controlSummary}</b>
            </Button>
            <Button
              type="button"
              variant="outline"
              className="mobile-dock-btn mobile-dock-btn-wide"
              data-testid="mobile-inspector-toggle"
              aria-expanded={inspectorOpen}
              aria-controls="mobile-inspector-body"
              onClick={() => { setMobileSheet("none"); returnFocusRef.current = true; setInspectorOpen(true); }}
            >
              <span>{t.evidence} / {priorityTitle}</span>
              <b>{selectedSummary}</b>
            </Button>
          </div>

          <Drawer open={mobileSheet === "about"} onOpenChange={(open) => setMobileSheet(open ? "about" : "none")} direction="bottom" modal={false}>
            <DrawerContent className="mobile-sheet-container shadcn-mobile-drawer" data-testid="mobile-about-sheet" aria-label={language === "es" ? "Acerca" : "About"}>
              <DrawerHeader className="mobile-sheet-header">
                <div className="mobile-sheet-handle" aria-hidden="true" />
                <div className="mobile-sheet-titlebar">
                  <div>
                    <DrawerTitle>{language === "es" ? "Acerca" : "About"}</DrawerTitle>
                    <DrawerDescription>{t.title}</DrawerDescription>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={() => setMobileSheet("none")}>{language === "es" ? "Cerrar" : "Close"}</Button>
                </div>
              </DrawerHeader>
              <ScrollArea className="mobile-sheet-content mobile-sheet-scroller">
                <div className="mobile-sheet-body">
                  <p>{t.subtitle}</p>
                  <p className="quick-start">{t.quickStart}</p>
                  {offlineLabel && (
                    <p className={`offline-line ${offlineState}`}>{offlineLabel}</p>
                  )}
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
                  <p className="muted">{t.rankingNote}</p>
                  <section className="downloads-section">
                    <h2>{t.downloads}</h2>
                    <DownloadGroups downloads={active?.downloads} language={language} aoiId={active?.id} surface="downloads_panel" />
                  </section>
                </div>
              </ScrollArea>
            </DrawerContent>
          </Drawer>

          <Drawer open={mobileSheet === "zona"} onOpenChange={(open) => setMobileSheet(open ? "zona" : "none")} direction="bottom" modal={false}>
            <DrawerContent className="mobile-sheet-container shadcn-mobile-drawer" data-testid="mobile-zona-sheet" aria-label={language === "es" ? "Ir a zona afectada" : "Go to affected area"}>
              <DrawerHeader className="mobile-sheet-header">
                <div className="mobile-sheet-handle" aria-hidden="true" />
                <div className="mobile-sheet-titlebar">
                  <div>
                    <DrawerTitle>{language === "es" ? "Ir a zona afectada" : "Go to affected area"}</DrawerTitle>
                    <DrawerDescription>{activeCity?.name[language] ?? ""}</DrawerDescription>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={() => setMobileSheet("none")}>{language === "es" ? "Cerrar" : "Close"}</Button>
                </div>
              </DrawerHeader>
              <ScrollArea className="mobile-sheet-content mobile-sheet-scroller">
                <div className="mobile-sheet-body mobile-zona-list">
                  {aoiListNode}
                  <p className="muted">{t.rankingNote}</p>
                </div>
              </ScrollArea>
            </DrawerContent>
          </Drawer>

          <Drawer open={mobileSheet === "capas"} onOpenChange={(open) => setMobileSheet(open ? "capas" : "none")} direction="bottom" modal={false}>
            <DrawerContent className="mobile-sheet-container shadcn-mobile-drawer" data-testid="mobile-capas-sheet" aria-label={t.controls}>
              <DrawerHeader className="mobile-sheet-header">
                <div className="mobile-sheet-handle" aria-hidden="true" />
                <div className="mobile-sheet-titlebar">
                  <div>
                    <DrawerTitle>{t.controls}</DrawerTitle>
                    <DrawerDescription>{controlSummary}</DrawerDescription>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={() => setMobileSheet("none")}>{language === "es" ? "Cerrar" : "Close"}</Button>
                </div>
              </DrawerHeader>
              <ScrollArea className="mobile-sheet-content mobile-sheet-scroller">
                <div className="mobile-sheet-body map-toolbar-body-sheet">
                  {controlsBodyNode}
                </div>
              </ScrollArea>
            </DrawerContent>
          </Drawer>

          <Drawer open={inspectorOpen} onOpenChange={setInspectorOpen} direction="bottom" modal={false}>
            <DrawerContent className="mobile-sheet-container shadcn-mobile-drawer" data-testid="mobile-inspector-sheet" aria-label={`${t.evidence} / ${priorityTitle}`}>
              <DrawerHeader className="mobile-sheet-header">
                <div className="mobile-sheet-handle" aria-hidden="true" />
                <div className="mobile-sheet-titlebar">
                  <div>
                    <DrawerTitle>{t.evidence} / {priorityTitle}</DrawerTitle>
                    <DrawerDescription>{selectedSummary}</DrawerDescription>
                  </div>
                  <Button type="button" variant="outline" size="sm" data-testid="mobile-inspector-close" onClick={() => setInspectorOpen(false)}>{language === "es" ? "Cerrar" : "Close"}</Button>
                </div>
              </DrawerHeader>
              <ScrollArea className="mobile-sheet-content mobile-sheet-scroller">
                <div className="mobile-sheet-body">
                  {renderInspectorBody("mobile-inspector-body", mobilePriorityRef)}
                </div>
              </ScrollArea>
            </DrawerContent>
          </Drawer>
        </>
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

function Evidence({
  feature,
  vlm,
  language,
  onBackToPriority,
  onCopyCoords,
}: {
  feature: DamageFeature;
  vlm?: VlmRecord;
  language: Language;
  onBackToPriority: () => void;
  onCopyCoords: (feature: DamageFeature) => void | Promise<void>;
}) {
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
        <button type="button" className="text-action" data-testid="copy-coordinates" onClick={() => void onCopyCoords(feature)}>
          {t.copyCoords}
        </button>
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
