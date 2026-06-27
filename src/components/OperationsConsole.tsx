"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import MapPanel from "./map/MapPanel";
import type { AoiCatalog, AoiRecord, DamageFeature, Language, VlmRecord } from "./types";

const copy = {
  en: {
    title: "Crisis Damage Intelligence",
    subtitle: "Static-first geospatial triage for earthquake response",
    live: "Public read-only",
    language: "Language",
    aoi: "Area of interest",
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
      "Official EMS vector labels are the source of record for this AOI. MiniMax-M3 VLM results are post-event-only triage aids unless before/after chips are explicitly available. They can prioritize review, but they are not confirmed damage.",
    statuses: {
      "test-fixture": "Readiness test",
      "official-vector": "Official EMS vector",
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
    aoi: "Area de interes",
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
      "Las etiquetas vectoriales oficiales de EMS son la fuente principal para este AOI. Los resultados MiniMax-M3 son triage auxiliar post-evento salvo que existan chips antes/despues explicitos. Sirven para priorizar revisión, no son daño confirmado.",
    statuses: {
      "test-fixture": "Prueba de preparación",
      "official-vector": "Vector oficial EMS",
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

export default function OperationsConsole() {
  const [catalog, setCatalog] = useState<AoiCatalog | null>(null);
  const [activeId, setActiveId] = useState("emsr884-aoi06-moron");
  const [language, setLanguage] = useState<Language>("es");
  const [filter, setFilter] = useState<Filter>("all");
  const [mode, setMode] = useState<Mode>("after");
  const [basemap, setBasemap] = useState<Basemap>("aerial");
  const [opacity, setOpacity] = useState(52);
  const [selected, setSelected] = useState<DamageFeature | null>(null);
  const [focusToken, setFocusToken] = useState(0);
  const [vlm, setVlm] = useState<Record<string, VlmRecord>>({});
  const [features, setFeatures] = useState<DamageFeature[]>([]);
  const rightRailRef = useRef<HTMLElement | null>(null);
  const priorityRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    fetch("/data/catalog.json").then((r) => r.json()).then(setCatalog);
  }, []);

  const active = useMemo<AoiRecord | undefined>(() => catalog?.aois.find((a) => a.id === activeId), [catalog, activeId]);

  useEffect(() => {
    if (!active?.layers.vlm) return;
    fetch(active.layers.vlm)
      .then((r) => r.text())
      .then((text) => {
        const entries = text.split("\n").filter(Boolean).map((line) => JSON.parse(line) as VlmRecord);
        setVlm(Object.fromEntries(entries.map((entry) => [entry.id, entry])));
      });
  }, [active]);

  useEffect(() => {
    if (!active?.layers.damage) return;
    fetch(active.layers.damage)
      .then((r) => r.json())
      .then((data: { features: DamageFeature[] }) => setFeatures(data.features ?? []));
  }, [active]);

  const t = copy[language];
  const metrics = active?.metrics;
  const hasBeforeImagery = Boolean(active?.layers.beforeTiles || active?.layers.beforeImage);
  const hasAfterImagery = Boolean(active?.layers.afterTiles || active?.layers.afterImage);
  const hasImagery = hasBeforeImagery || hasAfterImagery;
  const isDemo = active?.status === "test-fixture";
  const isExternalPrediction = active?.status === "external-prediction";
  const statusLabel = (status: string) => t.statuses[status as keyof typeof t.statuses] ?? status;
  const selectAoi = (id: string) => {
    setActiveId(id);
    setSelected(null);
    setFocusToken((value) => value + 1);
    setVlm({});
    setFeatures([]);
  };
  const selectPriorityFeature = (feature: DamageFeature) => {
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
    return [...features].sort((a, b) => score(b) - score(a)).slice(0, 12);
  }, [features, vlm]);

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
          <button className={language === "es" ? "active" : ""} onClick={() => setLanguage("es")}>ES</button>
          <button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button>
        </div>

        <label className="field-label">{t.aoi}</label>
        <div className="aoi-list">
          {catalog?.aois.map((aoi) => (
            <button key={aoi.id} data-testid={`aoi-${aoi.id}`} className={aoi.id === activeId ? "aoi-card active" : "aoi-card"} onClick={() => selectAoi(aoi.id)}>
              <span>{aoi.name[language]}</span>
              <small>{statusLabel(aoi.status)}</small>
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
              <a key={kind} href={href}>{kind.toUpperCase()}</a>
            ))}
          </div>
        </section>
      </aside>

      <section className="map-stage">
        {active && (
          <MapPanel
            aoi={active}
            mode={mode}
            opacity={opacity / 100}
            filter={filter}
            basemap={basemap}
            vlm={vlm}
            selectedId={selected?.properties.id}
            focusToken={focusToken}
            onSelect={setSelected}
          />
        )}
        <div className="map-toolbar">
          <div className="control-group">
            <span>{t.basemap}</span>
            <div className="button-row">
              <button data-testid="basemap-map" className={basemap === "map" ? "active" : ""} onClick={() => setBasemap("map")}>{t.mapBase}</button>
              <button data-testid="basemap-aerial" className={basemap === "aerial" ? "active" : ""} onClick={() => setBasemap("aerial")}>{t.aerialBase}</button>
            </div>
            <em className="control-note">{t.aerialBaseNote}</em>
          </div>
          <div className="control-group">
            <span>{t.mode}</span>
            <div className="button-row">
              <button data-testid="mode-before" disabled={!hasBeforeImagery} className={mode === "before" ? "active" : ""} onClick={() => setMode("before")}>{t.before}</button>
              <button data-testid="mode-after" disabled={!hasAfterImagery} className={mode === "after" ? "active" : ""} onClick={() => setMode("after")}>{t.after}</button>
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
              <button data-testid="filter-all" className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>{t.all}</button>
              <button data-testid="filter-severe" className={filter === "severe" ? "active" : ""} onClick={() => setFilter("severe")}>{t.severe}</button>
              <button data-testid="filter-vlm" className={filter === "vlm" ? "active" : ""} onClick={() => setFilter("vlm")}>{t.vlmOnly}</button>
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
            <div className="download-row"><a href={active.imagery.after.url} target="_blank">COG</a></div>
          </section>
        )}
        <section className="confidence-panel">
          <h2>{t.confidenceTitle}</h2>
          <p>{t.confidenceText}</p>
        </section>
        <section ref={priorityRef}>
          <h2>{language === "es" ? "Prioridad" : "Priority"}</h2>
          <div className="priority-list">
            {priorityFeatures.map((feature) => {
              const p = feature.properties;
              const label = String(vlm[p.id]?.vlm?.damage_class ?? p.damage_class ?? p.damage_gra ?? "candidate");
              return (
                <button key={p.id} data-testid={`priority-${p.id}`} className={selected?.properties.id === p.id ? "priority-row active" : "priority-row"} onClick={() => selectPriorityFeature(feature)}>
                  <b>{p.id}</b>
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

function Evidence({ feature, vlm, language, onBackToPriority }: { feature: DamageFeature; vlm?: VlmRecord; language: Language; onBackToPriority: () => void }) {
  const t = copy[language];
  const p = feature.properties;
  const chip = vlm?.post_event_chip ?? vlm?.triplet_chip?.replace(/^.*chips\//, "/data/chips/");
  const mapsUrl = typeof p.google_maps_url === "string" ? p.google_maps_url : "";
  return (
    <div className="evidence-body">
      <h3>{p.id}</h3>
      <dl>
        <div><dt>Pixel</dt><dd>{p.damage_class ?? p.damage_gra ?? p.confirmed_damage_class ?? "unknown"}</dd></div>
        <div><dt>Score</dt><dd>{p.damage_score ?? p.damage_percent ?? p.confirmed_damage_percent ?? "-"}</dd></div>
        <div><dt>VLM</dt><dd>{vlm?.vlm?.damage_class ?? "not reviewed"}</dd></div>
        <div><dt>VLM type</dt><dd>{vlm ? (vlm.vlm?.review_type ?? "post_event_only") : "-"}</dd></div>
        <div><dt>Priority</dt><dd>{vlm?.vlm?.action_priority ?? "-"}</dd></div>
      </dl>
      {vlm?.vlm?.evidence && <p className="evidence-text">{vlm.vlm.evidence}</p>}
      {vlm?.vlm?.uncertainty_reason && <p className="evidence-text"><b>Uncertainty:</b> {vlm.vlm.uncertainty_reason}</p>}
      {chip && <a href={chip} target="_blank">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="chip-preview" src={chip} alt="" loading="lazy" />
      </a>}
      <div className="download-row">
        {mapsUrl && <a href={mapsUrl} target="_blank">{t.maps}</a>}
        {chip && <a href={chip} target="_blank">{t.chip}</a>}
        <button type="button" className="text-action" onClick={onBackToPriority}>{t.backToPriority}</button>
      </div>
    </div>
  );
}
