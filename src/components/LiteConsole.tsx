"use client";

import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import type { AoiCatalog, AoiRecord, Language } from "./types";
import { DEFAULT_LANGUAGE, persistLang, readStoredLang, subscribeStoredLang } from "@/lib/lang";

type LiteCity = {
  id: string;
  primaryAoiId: string;
  sourceIds: string[];
  name: Record<Language, string>;
};

type LiteCitySummary = LiteCity & {
  officialConfirmed: number;
  officialPossible: number;
  monitor: number;
  external: number;
  imageryOnly: boolean;
  score: number;
  center: [number, number];
  downloads: Record<string, string>;
  status: string;
};

const liteCities: LiteCity[] = [
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
    name: { en: "La Guaira / Caraballeda", es: "La Guaira / Caraballeda" },
  },
  { id: "moron", primaryAoiId: "emsr884-aoi06-moron", sourceIds: ["emsr884-aoi06-moron", "emsr884-aoi06-moron-monitor01"], name: { en: "Moron", es: "Morón" } },
  { id: "san-felipe", primaryAoiId: "emsr884-aoi08-san-felipe", sourceIds: ["emsr884-aoi08-san-felipe", "emsr884-aoi08-san-felipe-monitor01"], name: { en: "San Felipe", es: "San Felipe" } },
  { id: "caracas", primaryAoiId: "emsr884-aoi02-caracas", sourceIds: ["emsr884-aoi02-caracas", "emsr884-aoi02-caracas-monitor01"], name: { en: "Caracas", es: "Caracas" } },
  { id: "santa-cruz", primaryAoiId: "emsr884-aoi05-santa-cruz", sourceIds: ["emsr884-aoi05-santa-cruz"], name: { en: "Santa Cruz", es: "Santa Cruz" } },
  { id: "antimano", primaryAoiId: "emsr884-aoi03-antimano", sourceIds: ["emsr884-aoi03-antimano"], name: { en: "Antimano", es: "Antímano" } },
  { id: "guacara", primaryAoiId: "emsr884-aoi10-guacara", sourceIds: ["emsr884-aoi10-guacara"], name: { en: "Guacara", es: "Guacara" } },
];

const copy = {
  es: {
    title: "Vista ligera",
    subtitle: "Consulta rápida para voluntarios y coordinadores no técnicos.",
    ops: "Consola operativa",
    timeline: "Cronología",
    loading: "Cargando catálogo público...",
    error: "No se pudo cargar el catálogo. Intenta de nuevo con mejor señal.",
    language: "Idioma",
    mapLabel: "Zonas afectadas",
    listLabel: "Prioridad pública",
    official: "oficiales destruidos/dañados",
    possible: "posibles oficiales",
    monitor: "MONIT01",
    external: "triage externo",
    imageryOnly: "solo imagen",
    noOfficial: "sin daño oficial publicado",
    warning: "EMS es la fuente oficial. Predicciones externas, VLM y reportes comunitarios son solo triage.",
    downloads: "Descargas rápidas",
    openOps: "Abrir consola operativa",
    fieldPacket: "Paquete de campo",
    noDownloads: "Sin descargas ligeras publicadas.",
    updated: "Actualizado",
  },
  en: {
    title: "Lite view",
    subtitle: "Fast public view for volunteers and nontechnical coordinators.",
    ops: "Operations console",
    timeline: "Timeline",
    loading: "Loading public catalog...",
    error: "Catalog could not load. Try again with a better connection.",
    language: "Language",
    mapLabel: "Affected zones",
    listLabel: "Public priority",
    official: "official destroyed/damaged",
    possible: "official possible",
    monitor: "MONIT01",
    external: "external triage",
    imageryOnly: "imagery only",
    noOfficial: "no official damage published",
    warning: "EMS is the official source. External predictions, VLM, and community reports are triage only.",
    downloads: "Quick downloads",
    openOps: "Open operations console",
    fieldPacket: "Field packet",
    noDownloads: "No lightweight downloads published.",
    updated: "Updated",
  },
};

const n = (value: unknown) => Number(value ?? 0) || 0;

function summarizeCity(group: LiteCity, byId: Map<string, AoiRecord>): LiteCitySummary | null {
  const records = group.sourceIds.map((id) => byId.get(id)).filter(Boolean) as AoiRecord[];
  if (!records.length) return null;
  const officialVectors = records.filter((record) => record.status === "official-vector");
  const monitorLayers = records.filter((record) => record.status === "official-monitor-points");
  const externalLayers = records.filter((record) => record.status === "external-prediction" || record.status === "external-gap");
  const primary = byId.get(group.primaryAoiId) ?? records[0];
  const officialConfirmed = officialVectors.reduce((sum, record) => sum + n(record.metrics.damagedConfirmed), 0);
  const officialPossible = officialVectors.reduce((sum, record) => sum + n(record.metrics.possibleDamage), 0);
  const monitor = monitorLayers.reduce((sum, record) => sum + n(record.metrics.features), 0);
  const external = externalLayers.reduce((sum, record) => sum + n(record.metrics.candidates ?? record.metrics.features), 0);
  const imageryOnly = records.every((record) => record.status === "imagery-only");
  return {
    ...group,
    officialConfirmed,
    officialPossible,
    monitor,
    external,
    imageryOnly,
    center: primary.center,
    downloads: primary.downloads,
    status: primary.status,
    score: officialConfirmed * 1000 + officialPossible * 160 + monitor * 80 + Math.min(external * 0.01, 80) + (imageryOnly ? 1 : 0),
  };
}

function citySummaryText(city: LiteCitySummary, language: Language) {
  const t = copy[language];
  const parts: string[] = [];
  if (city.officialConfirmed) parts.push(`${city.officialConfirmed} ${t.official}`);
  if (city.officialPossible) parts.push(`${city.officialPossible} ${t.possible}`);
  if (city.monitor) parts.push(`${city.monitor} ${t.monitor}`);
  if (city.external) parts.push(`${city.external} ${t.external}`);
  if (city.imageryOnly) parts.push(t.imageryOnly);
  return parts.join(" · ") || t.noOfficial;
}

function liteDownloads(downloads: Record<string, string>) {
  return Object.entries(downloads).filter(([kind]) => ["csv", "kml", "geojson"].includes(kind.toLowerCase())).slice(0, 3);
}

function mapPoint(city: LiteCitySummary, bounds: { minLat: number; maxLat: number; minLon: number; maxLon: number }) {
  const [lat, lon] = city.center;
  const left = ((lon - bounds.minLon) / Math.max(bounds.maxLon - bounds.minLon, 0.001)) * 82 + 9;
  const top = (1 - ((lat - bounds.minLat) / Math.max(bounds.maxLat - bounds.minLat, 0.001))) * 72 + 12;
  return { left: `${Math.min(Math.max(left, 6), 94)}%`, top: `${Math.min(Math.max(top, 8), 88)}%` };
}

export default function LiteConsole() {
  const [catalog, setCatalog] = useState<AoiCatalog | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const language = useSyncExternalStore(subscribeStoredLang, readStoredLang, () => DEFAULT_LANGUAGE);
  const [selectedId, setSelectedId] = useState("la-guaira");
  const t = copy[language];

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  useEffect(() => {
    fetch("/data/catalog.json")
      .then((response) => {
        if (!response.ok) throw new Error("catalog unavailable");
        return response.json() as Promise<AoiCatalog>;
      })
      .then((nextCatalog) => {
        setCatalog(nextCatalog);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, []);

  const cities = useMemo(() => {
    if (!catalog) return [];
    const byId = new Map(catalog.aois.map((aoi) => [aoi.id, aoi]));
    return liteCities
      .map((group) => summarizeCity(group, byId))
      .filter((city): city is LiteCitySummary => Boolean(city))
      .sort((a, b) => b.score - a.score || a.name[language].localeCompare(b.name[language]));
  }, [catalog, language]);

  const selected = cities.find((city) => city.id === selectedId) ?? cities[0];
  const bounds = useMemo(() => {
    const lats = cities.map((city) => city.center[0]);
    const lons = cities.map((city) => city.center[1]);
    return {
      minLat: Math.min(...lats, 9),
      maxLat: Math.max(...lats, 11),
      minLon: Math.min(...lons, -69),
      maxLon: Math.max(...lons, -66),
    };
  }, [cities]);

  const changeLanguage = (nextLanguage: Language) => {
    persistLang(nextLanguage);
  };

  return (
    <main className="lite-shell">
      <header className="lite-header">
        <div>
          <span className="status-pill">{t.title}</span>
          <h1>Respuesta Venezuela</h1>
          <p>{t.subtitle}</p>
        </div>
        <nav className="lite-nav" aria-label={language === "es" ? "Navegación" : "Navigation"}>
          <div className="segmented" aria-label={t.language}>
            <button type="button" className={language === "es" ? "active" : ""} aria-pressed={language === "es"} onClick={() => changeLanguage("es")}>ES</button>
            <button type="button" className={language === "en" ? "active" : ""} aria-pressed={language === "en"} onClick={() => changeLanguage("en")}>EN</button>
          </div>
          <Link className="lite-secondary-link" href="/timeline">{t.timeline}</Link>
          <Link className="lite-primary-link" href="/">{t.ops}</Link>
        </nav>
      </header>

      {status === "loading" && <p className="lite-status">{t.loading}</p>}
      {status === "error" && <p className="lite-status error">{t.error}</p>}

      {status === "ready" && (
        <section className="lite-grid">
          <section className="lite-map-panel" aria-label={t.mapLabel}>
            <div className="lite-map">
              <div className="lite-coast" aria-hidden="true" />
              {cities.map((city, index) => (
                <button
                  key={city.id}
                  type="button"
                  className={`lite-map-pin ${city.id === selected?.id ? "active" : ""}`}
                  style={mapPoint(city, bounds)}
                  aria-label={`${city.name[language]}: ${citySummaryText(city, language)}`}
                  onClick={() => setSelectedId(city.id)}
                >
                  {index + 1}
                </button>
              ))}
            </div>
            <p>{t.warning}</p>
          </section>

          <section className="lite-list-panel" aria-label={t.listLabel}>
            <div className="lite-section-heading">
              <h2>{t.listLabel}</h2>
              {catalog?.updatedAt && <span>{t.updated}: {new Date(catalog.updatedAt).toLocaleString(language === "es" ? "es-VE" : "en-US")}</span>}
            </div>
            <div className="lite-city-list">
              {cities.map((city, index) => (
                <button
                  key={city.id}
                  type="button"
                  className={`lite-city-row ${city.id === selected?.id ? "active" : ""}`}
                  onClick={() => setSelectedId(city.id)}
                >
                  <b>{index + 1}. {city.name[language]}</b>
                  <span>{citySummaryText(city, language)}</span>
                </button>
              ))}
            </div>
          </section>

          {selected && (
            <section className="lite-action-panel" aria-label={t.downloads}>
              <div className="lite-section-heading">
                <h2>{selected.name[language]}</h2>
                <span>{selected.primaryAoiId}</span>
              </div>
              <p>{citySummaryText(selected, language)}</p>
              <div className="lite-actions">
                <Link className="lite-primary-link" href="/">{t.openOps}</Link>
                {liteDownloads(selected.downloads).map(([kind, href]) => (
                  <a key={kind} href={href} data-analytics-event="data_download_clicked" data-analytics-aoi={selected.primaryAoiId} data-analytics-format={kind.toLowerCase()} data-analytics-surface="lite_view">
                    {kind.toUpperCase()}
                  </a>
                ))}
                {liteDownloads(selected.downloads).length === 0 && <span>{t.noDownloads}</span>}
              </div>
            </section>
          )}
        </section>
      )}
    </main>
  );
}
