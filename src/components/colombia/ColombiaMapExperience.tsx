"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useMemo, useState } from "react";
import type {
  ColombiaIncident,
  ColombiaLanguage,
  ColombiaMapMode,
  ColombiaMappingAoi,
  ColombiaMappingSnapshot,
} from "./types";
import styles from "../../app/colombia/colombia.module.css";

const ColombiaMapCanvas = dynamic(() => import("./ColombiaMapCanvas"), {
  ssr: false,
  loading: () => (
    <div className={styles.mapLoading} role="status">
      <span aria-hidden="true" />
      Cargando mapa / <span lang="en">Loading map</span>
    </div>
  ),
});

const registryHref = "/data/incidents/colombia-2026-08-10-san-jose-del-palmar.json";
const mappingHref = "/data/incidents/colombia-2026-08-10-emsr916-map.json";
const externalLinkProps = {
  target: "_blank",
  rel: "noreferrer noopener",
} as const;

const copy = {
  es: {
    skip: "Ir al mapa",
    back: "Venezuela",
    title: "Mapa operativo del sismo",
    verified: "Verificado",
    mapModes: "Imagen del mapa",
    map: "Mapa",
    reference: "Referencia",
    before: "Antes",
    after: "Después",
    unavailable: "Aún no disponible",
    referenceWarning: "Referencia visual · fecha de captura no verificada",
    referenceDetail:
      "Esta imagen ayuda a orientarse. No es una capa anterior ni posterior al sismo y no demuestra daños.",
    scheduled: "Adquisición programada",
    waitingSummary:
      "Antes/Después se activará cuando exista cobertura fechada, licenciada y verificable.",
    areas: "Áreas oficiales de cartografía",
    areaBoundaryWarning:
      "Estas huellas indican dónde Copernicus está produciendo mapas; no son límites de daños.",
    overview: "Ver las 4 áreas",
    selectedArea: "Área seleccionada",
    product: "Producto",
    sensor: "Sensor",
    acquisition: "Captura programada",
    delivery: "Entrega estimada",
    waiting: "En espera",
    officialStatus: "Estado oficial",
    noTsunami: "Sin amenaza de tsunami",
    facts: "Datos del evento",
    magnitude: "Magnitud",
    depth: "Profundidad",
    epicenter: "Epicentro",
    sourceMethod: "Fuentes y método",
    sourcePolicy: "Cómo leer este mapa",
    sourceNote:
      "Solo se muestran geometrías oficiales o capas con fuente, fecha, licencia y alcance identificables. La ausencia de una capa no significa ausencia de daños.",
    data: "Datos",
    liveActivation: "Activación Copernicus",
    checked: "Consulta de Copernicus",
    eventRegistry: "Registro del evento",
    mapSnapshot: "Instantánea del mapa",
    external: "Abrir fuente",
    legendEpicenter: "Epicentro SGC",
    legendDamage: "Evaluación de daños prevista",
    legendMovement: "Movimiento del terreno previsto",
    currentView: "Vista actual",
  },
  en: {
    skip: "Go to map",
    back: "Venezuela",
    title: "Earthquake operations map",
    verified: "Verified",
    mapModes: "Map imagery",
    map: "Map",
    reference: "Reference",
    before: "Before",
    after: "After",
    unavailable: "Not available yet",
    referenceWarning: "Visual reference · capture date unverified",
    referenceDetail:
      "This imagery supports orientation. It is not a pre- or post-event layer and does not establish damage.",
    scheduled: "Acquisition scheduled",
    waitingSummary:
      "Before/After will activate when dated, licensed, verifiable coverage is available.",
    areas: "Official mapping areas",
    areaBoundaryWarning:
      "These footprints show where Copernicus is producing maps; they are not damage boundaries.",
    overview: "View all 4 areas",
    selectedArea: "Selected area",
    product: "Product",
    sensor: "Sensor",
    acquisition: "Scheduled capture",
    delivery: "Expected delivery",
    waiting: "Waiting",
    officialStatus: "Official status",
    noTsunami: "No tsunami threat",
    facts: "Event facts",
    magnitude: "Magnitude",
    depth: "Depth",
    epicenter: "Epicenter",
    sourceMethod: "Sources and method",
    sourcePolicy: "How to read this map",
    sourceNote:
      "Only official geometries or layers with identifiable source, date, license, and scope are shown. The absence of a layer does not mean an absence of damage.",
    data: "Data",
    liveActivation: "Copernicus activation",
    checked: "Copernicus check",
    eventRegistry: "Event registry",
    mapSnapshot: "Map snapshot",
    external: "Open source",
    legendEpicenter: "SGC epicenter",
    legendDamage: "Planned damage assessment",
    legendMovement: "Planned ground movement",
    currentView: "Current view",
  },
} as const;

function localizedDate(value: string | null, language: ColombiaLanguage) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(language === "es" ? "es-CO" : "en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Bogota",
  }).format(new Date(value));
}

function firstProduct(aoi: ColombiaMappingAoi | null) {
  return aoi?.products[0] ?? null;
}

export default function ColombiaMapExperience({
  incident,
  mapping,
}: {
  incident: ColombiaIncident;
  mapping: ColombiaMappingSnapshot;
}) {
  const [language, setLanguage] = useState<ColombiaLanguage>("es");
  const [mode, setMode] = useState<ColombiaMapMode>("reference");
  const [selectedAoiId, setSelectedAoiId] = useState<string | null>(null);
  const text = copy[language];
  const selectedAoi = useMemo(
    () => mapping.aois.find((aoi) => aoi.id === selectedAoiId) ?? null,
    [mapping.aois, selectedAoiId],
  );
  const product = firstProduct(selectedAoi);
  const image = product?.images[0] ?? null;

  const setAoi = (aoiId: string | null) => {
    setSelectedAoiId(aoiId);
  };

  const modes: Array<{
    id: ColombiaMapMode;
    label: string;
    available: boolean;
  }> = [
    { id: "map", label: text.map, available: true },
    { id: "reference", label: text.reference, available: true },
    { id: "before", label: text.before, available: Boolean(mapping.imagery.before) },
    { id: "after", label: text.after, available: Boolean(mapping.imagery.after) },
  ];

  const prioritySources = incident.sources.filter((source) =>
    ["sgc-seismic-viewer", "dimar-bulletin-01", "ungrd-initial-response"].includes(source.id),
  );

  return (
    <main
      className={styles.page}
      data-incident-id={incident.incidentId}
      data-status={incident.status}
      data-map-activation={mapping.activationCode}
    >
      <a className={styles.skipLink} href="#mapa-colombia">
        {text.skip}
      </a>

      <aside className={styles.rail} aria-label={language === "es" ? "Panel del incidente" : "Incident panel"}>
        <header className={styles.railHeader}>
          <div className={styles.navRow}>
            <Link href="/" className={styles.backLink}>
              <span aria-hidden="true">←</span> {text.back}
            </Link>
            <div className={styles.languageControl} aria-label="Idioma / Language">
              <button
                type="button"
                className={language === "es" ? styles.active : undefined}
                aria-pressed={language === "es"}
                onClick={() => setLanguage("es")}
              >
                ES
              </button>
              <button
                type="button"
                className={language === "en" ? styles.active : undefined}
                aria-pressed={language === "en"}
                onClick={() => setLanguage("en")}
              >
                EN
              </button>
            </div>
          </div>

          <div className={styles.identity}>
            <p>RESPUESTA · COLOMBIA</p>
            <span>{mapping.activationCode}</span>
          </div>
          <h1>{text.title}</h1>
          <p className={styles.eventTitle}>{incident.event.title[language]}</p>
          <div className={styles.verifiedLine}>
            <span className={styles.liveDot} aria-hidden="true" />
            <strong>{text.verified}</strong>
            <time dateTime={mapping.lastCheckedAt}>{localizedDate(mapping.lastCheckedAt, language)}</time>
          </div>
        </header>

        <section className={styles.factStrip} aria-label={text.facts}>
          <div>
            <span>{text.magnitude}</span>
            <strong>M{incident.event.magnitude}</strong>
          </div>
          <div>
            <span>{text.depth}</span>
            <strong>{incident.event.depthKm} km</strong>
          </div>
          <div>
            <span>{text.officialStatus}</span>
            <strong>{text.noTsunami}</strong>
          </div>
        </section>

        <section className={styles.controlSection} aria-labelledby="imagery-controls">
          <div className={styles.sectionLabelRow}>
            <h2 id="imagery-controls">{text.mapModes}</h2>
            <span>{mapping.imagery.comparisonState === "ready" ? "READY" : "WAITING"}</span>
          </div>
          <div className={styles.modeControl}>
            {modes.map((item) => (
              <button
                key={item.id}
                type="button"
                className={mode === item.id ? styles.active : undefined}
                aria-pressed={mode === item.id}
                disabled={!item.available}
                aria-describedby={!item.available ? "comparison-waiting" : undefined}
                title={!item.available ? text.unavailable : undefined}
                onClick={() => setMode(item.id)}
              >
                {item.label}
                {!item.available ? <span aria-hidden="true">·</span> : null}
              </button>
            ))}
          </div>
          <div
            className={mode === "reference" ? styles.referenceNotice : styles.waitingNotice}
            id="comparison-waiting"
            role="status"
          >
            <strong>{mode === "reference" ? text.referenceWarning : text.scheduled}</strong>
            <p>{mode === "reference" ? text.referenceDetail : text.waitingSummary}</p>
          </div>
        </section>

        <section className={styles.controlSection} aria-labelledby="aoi-heading">
          <div className={styles.sectionLabelRow}>
            <h2 id="aoi-heading">{text.areas}</h2>
            <button type="button" className={styles.overviewButton} onClick={() => setAoi(null)}>
              {text.overview}
            </button>
          </div>
          <p className={styles.boundaryWarning}>{text.areaBoundaryWarning}</p>
          <div className={styles.aoiList}>
            {mapping.aois.map((aoi) => {
              const aoiProduct = firstProduct(aoi);
              const selected = aoi.id === selectedAoiId;
              return (
                <button
                  key={aoi.id}
                  type="button"
                  className={selected ? styles.selectedAoi : undefined}
                  aria-pressed={selected}
                  onClick={() => setAoi(aoi.id)}
                  data-testid={`colombia-aoi-${String(aoi.number).padStart(2, "0")}`}
                >
                  <span>AOI {String(aoi.number).padStart(2, "0")}</span>
                  <strong>{aoi.name[language]}</strong>
                  <small>
                    {aoiProduct?.typeLabel[language]} · {text.waiting}
                  </small>
                </button>
              );
            })}
          </div>
        </section>

        {selectedAoi && product ? (
          <section className={styles.selectionCard} aria-labelledby="selected-aoi-heading">
            <p>{text.selectedArea}</p>
            <h2 id="selected-aoi-heading">{selectedAoi.name[language]}</h2>
            <dl>
              <div>
                <dt>{text.product}</dt>
                <dd>{product.typeLabel[language]}</dd>
              </div>
              <div>
                <dt>{text.sensor}</dt>
                <dd>{image ? `${image.sensor} · ${image.resolutionClass}` : "—"}</dd>
              </div>
              <div>
                <dt>{text.acquisition}</dt>
                <dd>{localizedDate(image?.acquisitionUtc ?? null, language)}</dd>
              </div>
              <div>
                <dt>{text.delivery}</dt>
                <dd>{localizedDate(product.expectedDeliveryUtc, language)}</dd>
              </div>
            </dl>
          </section>
        ) : null}

        <details className={styles.sources}>
          <summary>{text.sourceMethod}</summary>
          <div className={styles.sourcesBody}>
            <h2>{text.sourcePolicy}</h2>
            <p>{text.sourceNote}</p>
            <ul>
              <li>
                <a href={mapping.situationUrl} {...externalLinkProps}>
                  Copernicus EMSR916 <span aria-hidden="true">↗</span>
                </a>
              </li>
              {prioritySources.map((source) => (
                <li key={source.id}>
                  <a href={source.url} {...externalLinkProps}>
                    {source.label[language]} <span aria-hidden="true">↗</span>
                  </a>
                </li>
              ))}
            </ul>
            <div className={styles.dataLinks}>
              <span>{text.data}</span>
              <a href={registryHref}>{text.eventRegistry}</a>
              <a href={mappingHref}>{text.mapSnapshot}</a>
            </div>
          </div>
        </details>
      </aside>

      <section className={styles.mapStage} aria-label={text.currentView}>
        <ColombiaMapCanvas
          mapping={mapping}
          mode={mode}
          language={language}
          selectedAoiId={selectedAoiId}
          epicenter={{
            longitude: incident.event.longitude,
            latitude: incident.event.latitude,
          }}
          onSelectAoi={setAoi}
        />

        <div className={styles.mapStatusCard} aria-live="polite">
          <span>{mode === "reference" ? text.referenceWarning : text.currentView}</span>
          <strong>
            {selectedAoi ? selectedAoi.name[language] : text.overview}
          </strong>
          <small>
            {mode === "reference"
              ? mapping.imagery.reference.source
              : mode === "map"
                ? "OpenStreetMap"
                : mode === "before"
                  ? text.before
                  : text.after}
          </small>
        </div>

        <div className={styles.mapLegend} aria-label={language === "es" ? "Leyenda" : "Legend"}>
          <span>
            <i className={styles.epicenterKey} aria-hidden="true" />
            {text.legendEpicenter}
          </span>
          <span>
            <i className={styles.damageKey} aria-hidden="true" />
            {text.legendDamage}
          </span>
          <span>
            <i className={styles.movementKey} aria-hidden="true" />
            {text.legendMovement}
          </span>
        </div>
      </section>
    </main>
  );
}
