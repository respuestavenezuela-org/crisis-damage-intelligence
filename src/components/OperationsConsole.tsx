"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { trackAnalytics } from "@/lib/analytics";
import MapPanel from "./map/MapPanel";
import type { AoiCatalog, AoiRecord, DamageFeature, Language, VlmRecord } from "./types";

const copy = {
  en: {
    title: "Crisis Damage Intelligence",
    subtitle: "Static-first geospatial triage for earthquake response",
    live: "Public read-only",
    language: "Language",
    aoi: "Go to affected area",
    source: "Source",
    status: "Status",
    features: "features",
    candidates: "candidates",
    confirmed: "official destroyed/damaged",
    possible: "official possible",
    vlm: "VLM reviewed",
    mode: "Image",
    basemap: "Base",
    mapBase: "Map",
    aerialBase: "Aerial",
    aerialBaseNote: "Reference imagery only. Damage evidence comes from EMS vectors and post-event AOI imagery.",
    before: "Before",
    after: "After",
    noImagery: "No imagery exposed for this AOI yet",
    noBefore: "Before imagery is not exposed yet. Showing post-event imagery where available.",
    imageryAvailable: "Post-event imagery available",
    imageryOnly: "Imagery only - no official damage vector yet",
    opacity: "Damage opacity",
    filters: "Filters",
    all: "All",
    severe: "Destroyed/Damaged",
    vlmOnly: "VLM reviewed",
    filterNote: "Severity uses official EMS damage_gra when available. Possible damage is not counted as destroyed/damaged.",
    downloads: "Downloads",
    evidence: "Evidence queue",
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
    },
  },
  es: {
    title: "Inteligencia de Daños en Crisis",
    subtitle: "Triage geoespacial static-first para respuesta a terremotos",
    live: "Publico solo lectura",
    language: "Idioma",
    aoi: "Ir a zona afectada",
    source: "Fuente",
    status: "Estado",
    features: "estructuras",
    candidates: "candidatos",
    confirmed: "destruidos/dañados oficiales",
    possible: "posibles oficiales",
    vlm: "revisados VLM",
    mode: "Imagen",
    basemap: "Base",
    mapBase: "Mapa",
    aerialBase: "Aerea",
    aerialBaseNote: "Imagen de referencia solamente. La evidencia de daño viene de vectores EMS e imagen posterior por AOI.",
    before: "Antes",
    after: "Despues",
    noImagery: "Sin imagen expuesta para este AOI todavia",
    noBefore: "La imagen antes no esta expuesta todavia. Se muestra imagen posterior donde exista.",
    imageryAvailable: "Imagen posterior disponible",
    imageryOnly: "Solo imagen - sin vector oficial de danos aun",
    opacity: "Opacidad de daño",
    filters: "Filtros",
    all: "Todos",
    severe: "Destruido/Dañado",
    vlmOnly: "Revisado VLM",
    filterNote: "La severidad usa damage_gra oficial de EMS cuando existe. Posible daño no cuenta como destruido/dañado.",
    downloads: "Descargas",
    evidence: "Cola de evidencia",
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
    },
  },
};

type Filter = "all" | "severe" | "vlm";
type Mode = "before" | "after";
type Basemap = "map" | "aerial";
type CityNavItem = {
  id: string;
  primaryAoiId: string;
  sourceIds: string[];
  name: Record<Language, string>;
  official: number;
  monitor: number;
  external: number;
  imageryOnly: boolean;
  score: number;
};

let appLoadedTracked = false;

const cityGroups: Array<Omit<CityNavItem, "official" | "monitor" | "external" | "imageryOnly" | "score">> = [
  {
    id: "la-guaira",
    primaryAoiId: "emsr884-aoi12-caraballeda",
    sourceIds: ["emsr884-aoi12-caraballeda", "external-msft-catia-la-mar-predicted-damage"],
    name: { en: "La Guaira / Caraballeda / Catia La Mar", es: "La Guaira / Caraballeda / Catia La Mar" },
  },
  {
    id: "san-felipe",
    primaryAoiId: "emsr884-aoi08-san-felipe",
    sourceIds: ["emsr884-aoi08-san-felipe", "emsr884-aoi08-san-felipe-monitor01"],
    name: { en: "San Felipe", es: "San Felipe" },
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
  if (item.official) parts.push(language === "es" ? `${item.official} oficiales` : `${item.official} official`);
  if (item.monitor) parts.push(language === "es" ? `${item.monitor} monitor` : `${item.monitor} monitor`);
  if (item.external) parts.push(language === "es" ? `${item.external} predicción externa` : `${item.external} external prediction`);
  return parts.join(" · ") || (language === "es" ? "0 daños oficiales" : "0 official damage");
}

export default function OperationsConsole() {
  const [catalog, setCatalog] = useState<AoiCatalog | null>(null);
  const [activeId, setActiveId] = useState("emsr884-aoi12-caraballeda");
  const [language, setLanguage] = useState<Language>("es");
  const [filter, setFilter] = useState<Filter>("all");
  const [mode, setMode] = useState<Mode>("after");
  const [basemap, setBasemap] = useState<Basemap>("aerial");
  const [opacity, setOpacity] = useState(52);
  const [selected, setSelected] = useState<DamageFeature | null>(null);
  const [focusToken, setFocusToken] = useState(0);
  const [aoiFocusToken, setAoiFocusToken] = useState(0);
  const [vlm, setVlm] = useState<Record<string, VlmRecord>>({});
  const [features, setFeatures] = useState<DamageFeature[]>([]);
  const rightRailRef = useRef<HTMLElement | null>(null);
  const priorityRef = useRef<HTMLElement | null>(null);
  const appLoadTrackedRef = useRef(false);

  useEffect(() => {
    fetch("/data/catalog.json").then((r) => r.json()).then(setCatalog);
  }, []);

  const active = useMemo<AoiRecord | undefined>(() => catalog?.aois.find((a) => a.id === activeId), [catalog, activeId]);

  useEffect(() => {
    if (!catalog) return;
    let cancelled = false;
    Promise.all(
      catalog.aois.map(async (aoi) => {
        if (!aoi.layers.vlm) return [];
        const text = await fetch(aoi.layers.vlm).then((r) => r.text());
        return text.split("\n").filter(Boolean).map((line) => {
          const entry = JSON.parse(line) as VlmRecord;
          return [`${aoi.id}__${entry.id}`, entry] as const;
        });
      }),
    ).then((groups) => {
      if (!cancelled) setVlm(Object.fromEntries(groups.flat()));
    });
    return () => { cancelled = true; };
  }, [catalog]);

  useEffect(() => {
    if (!catalog) return;
    let cancelled = false;
    Promise.all(
      catalog.aois.map(async (aoi) => {
        const data = await fetch(aoi.layers.damage).then((r) => r.json()) as { features: DamageFeature[] };
        return (data.features ?? []).map((feature) => {
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
      }),
    ).then((groups) => {
      if (!cancelled) setFeatures(groups.flat());
    });
    return () => { cancelled = true; };
  }, [catalog]);

  const t = copy[language];
  const metrics = active?.metrics;
  const hasBeforeImagery = Boolean(active?.layers.beforeTiles || active?.layers.beforeImage);
  const hasAfterImagery = Boolean(active?.layers.afterTiles || active?.layers.afterImage);
  const hasImagery = hasBeforeImagery || hasAfterImagery;
  const isDemo = active?.status === "test-fixture";
  const isExternalPrediction = active?.status === "external-prediction";
  const statusLabel = (status: string) => t.statuses[status as keyof typeof t.statuses] ?? status;
  const cityNavItems = useMemo<CityNavItem[]>(() => {
    if (!catalog) return [];
    const byId = new Map(catalog.aois.map((aoi) => [aoi.id, aoi]));
    return cityGroups.map((group) => {
      const records = group.sourceIds.map((id) => byId.get(id)).filter(Boolean) as AoiRecord[];
      const official = records
        .filter((aoi) => aoi.status === "official-vector")
        .reduce((sum, aoi) => sum + (aoi.metrics.features ?? 0), 0);
      const monitor = records
        .filter((aoi) => aoi.status === "official-monitor-points")
        .reduce((sum, aoi) => sum + (aoi.metrics.features ?? 0), 0);
      const external = records
        .filter((aoi) => aoi.status === "external-prediction")
        .reduce((sum, aoi) => sum + (aoi.metrics.candidates ?? aoi.metrics.features ?? 0), 0);
      const imageryOnly = records.length > 0 && records.every((aoi) => aoi.status === "imagery-only");
      return {
        ...group,
        official,
        monitor,
        external,
        imageryOnly,
        score: official + monitor + external,
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

  const changeLanguage = (nextLanguage: Language) => {
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
    setSelected(null);
    setFocusToken((value) => value + 1);
    setAoiFocusToken((value) => value + 1);
  };
  const changeMode = (nextMode: Mode) => {
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
    if (nextBasemap !== basemap) {
      trackAnalytics("basemap_changed", {
        aoi_id: activeId,
        basemap: nextBasemap,
      });
    }
    setBasemap(nextBasemap);
  };
  const changeFilter = (nextFilter: Filter) => {
    if (nextFilter !== filter) {
      trackAnalytics("damage_filter_changed", {
        aoi_id: activeId,
        filter: nextFilter,
      });
    }
    setFilter(nextFilter);
  };
  const selectPriorityFeature = (feature: DamageFeature, rank: number) => {
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
    setFocusToken((value) => value + 1);
    rightRailRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };
  const scrollToPriority = () => {
    priorityRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const adjustOpacity = (delta: number) => setOpacity((value) => Math.max(5, Math.min(90, value + delta)));
  const priorityFeatures = useMemo(() => {
    const score = (feature: DamageFeature) => {
      const p = feature.properties;
      const id = p.id;
      const cls = String(vlm[id]?.vlm?.damage_class ?? p.damage_class ?? p.damage_gra ?? "").toLowerCase();
      const numeric = Number(p.damage_score ?? p.damage_percent ?? p.confirmed_damage_percent ?? 0);
      if (vlm[id]) return 400 + numeric;
      if (cls.includes("destroy") || cls.includes("major") || cls === "damaged") return 300 + numeric;
      if (cls.includes("possible") || cls.includes("minor")) return 200 + numeric;
      return numeric;
    };
    return features.filter((feature) => feature.properties.aoi_id === activeId).sort((a, b) => score(b) - score(a)).slice(0, 12);
  }, [activeId, features, vlm]);

  return (
    <main className="ops-shell">
      <aside className="left-rail">
        <div className="brand-block">
          <div className="status-pill">{t.live}</div>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>

        <label className="field-label">{t.language}</label>
        <div className="segmented" aria-label={t.language}>
          <button className={language === "es" ? "active" : ""} onClick={() => changeLanguage("es")}>ES</button>
          <button className={language === "en" ? "active" : ""} onClick={() => changeLanguage("en")}>EN</button>
        </div>

        <label className="field-label">{t.aoi}</label>
        <div className="aoi-list">
          {cityNavItems.map((item) => (
            <button key={item.id} data-testid={`city-${item.id}`} className={item.sourceIds.includes(activeId) ? "aoi-card active" : "aoi-card"} onClick={() => selectAoi(item.primaryAoiId, item.id)}>
              <span>{item.name[language]}</span>
              <small>{cityImpactLabel(item, language)}</small>
            </button>
          ))}
        </div>

        {active && (
          <section className="source-card">
            <div className={(isDemo || isExternalPrediction) ? "source-banner demo" : "source-banner official"}>
              {isDemo ? t.demoOnly : isExternalPrediction ? t.externalPrediction : t.officialData}
            </div>
            <strong>{t.source}</strong>
            <p>{active.source}</p>
            <div className="meta-row"><span>{t.status}</span><b>{statusLabel(active.status)}</b></div>
          </section>
        )}

        <section className="kpi-grid">
          <div><b>{metrics?.features ?? "-"}</b><span>{t.features}</span></div>
          <div><b>{metrics?.damagedConfirmed ?? 0}</b><span>{t.confirmed}</span></div>
          <div><b>{metrics?.candidates ?? metrics?.possibleDamage ?? 0}</b><span>{t.candidates}</span></div>
          <div><b>{metrics?.vlmReviewed ?? 0}</b><span>{t.vlm}</span></div>
        </section>

        <section className="downloads-section">
          <h2>{t.downloads}</h2>
          <div className="download-row">
            {active && Object.entries(active.downloads).map(([kind, href]) => (
              <a
                key={kind}
                href={href}
                data-analytics-event="data_download_clicked"
                data-analytics-aoi={active.id}
                data-analytics-format={kind.toLowerCase()}
                data-analytics-surface="downloads_panel"
              >
                {kind.toUpperCase()}
              </a>
            ))}
          </div>
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
            onSelect={setSelected}
          />
        )}
        <div className="map-toolbar">
          <div className="control-group">
            <span>{t.basemap}</span>
            <div className="button-row">
              <button data-testid="basemap-map" className={basemap === "map" ? "active" : ""} onClick={() => changeBasemap("map")}>{t.mapBase}</button>
              <button data-testid="basemap-aerial" className={basemap === "aerial" ? "active" : ""} onClick={() => changeBasemap("aerial")}>{t.aerialBase}</button>
            </div>
            <em className="control-note">{t.aerialBaseNote}</em>
          </div>
          <div className="control-group">
            <span>{t.mode}</span>
            <div className="button-row">
              <button data-testid="mode-before" disabled={!hasBeforeImagery} className={mode === "before" ? "active" : ""} onClick={() => changeMode("before")}>{t.before}</button>
              <button data-testid="mode-after" disabled={!hasAfterImagery} className={mode === "after" ? "active" : ""} onClick={() => changeMode("after")}>{t.after}</button>
            </div>
            {!hasImagery && <em className="control-note">{t.noImagery}</em>}
            {hasAfterImagery && !hasBeforeImagery && <em className="control-note">{t.noBefore}</em>}
          </div>
          <label className="range-control">
            <span>{t.opacity} <b>{opacity}%</b></span>
            <div className="range-row">
              <button type="button" aria-label="reduce damage opacity" onClick={() => adjustOpacity(-10)}>-</button>
              <input type="range" min="5" max="90" value={opacity} onInput={(e) => setOpacity(Number(e.currentTarget.value))} onChange={(e) => setOpacity(Number(e.currentTarget.value))} />
              <button type="button" aria-label="increase damage opacity" onClick={() => adjustOpacity(10)}>+</button>
            </div>
          </label>
          <div className="control-group">
            <span>{t.filters}</span>
            <div className="button-row">
              <button data-testid="filter-all" className={filter === "all" ? "active" : ""} onClick={() => changeFilter("all")}>{t.all}</button>
              <button data-testid="filter-severe" className={filter === "severe" ? "active" : ""} onClick={() => changeFilter("severe")}>{t.severe}</button>
              <button data-testid="filter-vlm" className={filter === "vlm" ? "active" : ""} onClick={() => changeFilter("vlm")}>{t.vlmOnly}</button>
            </div>
            <em className="control-note">{t.filterNote}</em>
          </div>
        </div>
      </section>

      <aside className="right-rail" ref={rightRailRef}>
        <section className="evidence-panel">
          <h2>{t.evidence}</h2>
          {selected ? (
            <Evidence feature={selected} vlm={vlm[selected.properties.id]} language={language} onBackToPriority={scrollToPriority} />
          ) : (
            <p className="muted">{t.noSelection}</p>
          )}
        </section>
        {active?.imagery?.after && (
          <section className="imagery-panel">
            <h2>{t.imageryAvailable}</h2>
            <dl>
              <div><dt>AOI</dt><dd>{active.id}</dd></div>
              <div><dt>Sensor</dt><dd>{active.imagery.after.sensor ?? "-"}</dd></div>
              <div><dt>UTC</dt><dd>{active.imagery.after.acquisitionUtc ?? "-"}</dd></div>
              <div><dt>Size</dt><dd>{formatBytes(active.imagery.after.bytes)}</dd></div>
            </dl>
            {!active.metrics.features && <p className="muted">{t.imageryOnly}</p>}
            <div className="download-row">
              <a
                href={active.imagery.after.url}
                target="_blank"
                rel="noreferrer"
                data-analytics-event="data_download_clicked"
                data-analytics-aoi={active.id}
                data-analytics-format="cog"
                data-analytics-surface="imagery_panel"
              >
                COG
              </a>
            </div>
          </section>
        )}
        <section className="confidence-panel">
          <h2>{t.confidenceTitle}</h2>
          <p>{t.confidenceText}</p>
        </section>
        {active && <VlmQualityPanel aoi={active} language={language} />}
        <section ref={priorityRef}>
          <h2>{language === "es" ? "Prioridad" : "Priority"}</h2>
          <div className="priority-list">
            {priorityFeatures.map((feature, index) => {
              const p = feature.properties;
              const label = String(vlm[p.id]?.vlm?.damage_class ?? p.damage_class ?? p.damage_gra ?? "candidate");
              return (
                <button key={p.id} data-testid={`priority-${p.source_feature_id ?? p.id}`} className={selected?.properties.id === p.id ? "priority-row active" : "priority-row"} onClick={() => selectPriorityFeature(feature, index + 1)}>
                  <b>{p.source_feature_id ?? p.id}</b>
                  <span>{label} · {String(p.damage_score ?? p.damage_percent ?? "-")}</span>
                </button>
              );
            })}
          </div>
        </section>
        <section>
          <h2>{t.watchlist}</h2>
          {catalog?.watchlist.map((item) => (
            <div className="watch-row" key={item.id}>
              <b>{item.name[language]}</b>
              <span>{statusLabel(item.status)} · {item.expectedUtc}</span>
            </div>
          ))}
        </section>
        <section className="architecture">
          <h2>{t.architecture}</h2>
          <p>{t.architectureText}</p>
        </section>
      </aside>
    </main>
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
  const mapsUrl = typeof p.google_maps_url === "string" ? p.google_maps_url : "";
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
        <img className="chip-preview" src={chip.url} alt="" loading="lazy" />
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
