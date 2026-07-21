"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState, useSyncExternalStore } from "react";
import { DEFAULT_LANGUAGE, persistLang, readStoredLang, subscribeStoredLang } from "@/lib/lang";
import type { Language } from "@/components/types";
import type {
  AerialEvidenceCollection,
  First72Finding,
  ReconstructionConfidence,
  ReconstructionCatalog,
  ReconstructionData,
  ReconstructionEvent,
  ReconstructionSource,
  ResponseStage,
} from "./types";
import styles from "./timeline.module.css";

const copy = {
  es: {
    reconstruction: "Reconstrucción pública · evidencia en desarrollo",
    title: "Lo que pasó después",
    openMap: "Abrir mapa de daños",
    scope: "Alcance",
    evidenceCutoff: "Evidencia más reciente",
    sources: "Fuentes registradas",
    events: "Eventos reconstruidos",
    first72: "Las primeras 72 horas",
    first72Kicker: "La pregunta crítica",
    first72Question: "¿Cuándo llegó la ayuda — y cuándo llegó realmente a los sitios?",
    assessment: "Evaluación actual",
    evidenceRule: "Cómo leer esta conclusión",
    evidenceRuleText: "Anunciado, movilizado, llegado, observado y operativo son estados distintos. El atlas no los mezcla.",
    filters: "Filtrar la cronología",
    all: "Todo",
    timeline: "Cronología de la respuesta",
    timelineIntro: "Cada entrada distingue lo observado de lo inferido y enlaza las fuentes que sostienen la descripción.",
    first72Only: "Dentro de 72 h",
    after72: "Después de 72 h",
    evidence: "evidencia",
    source: "fuente",
    sourcePlural: "fuentes",
    openSource: "Abrir fuente",
    sourceLedger: "Registro de fuentes",
    sourceLedgerIntro: "Se enlaza el material original. Cuando la licencia de reutilización no está clara, no copiamos la imagen ni el documento.",
    method: "Método y límites",
    notObserved: "No observado ≠ no ocurrió",
    arrivalStages: "Llegar no es una sola cosa",
    imageEvidence: "Evidencia de imagen",
    imageCaveat: "La detección de vehículos o maquinaria es candidata hasta revisión humana. Una imagen no prueba propiedad, función, suficiencia ni movimiento.",
    latest: "Última actualización",
    backToTop: "Volver arriba",
    present: "Presencia",
    areaIndex: "Reconstrucciones publicadas",
    areaIndexIntro: "Cambia de territorio sin perder las reglas de evidencia.",
    officialRecord: "Registro oficial EMS",
    confirmedDamage: "destruidos/dañados",
    possibleDamage: "posibles",
    evidenceGaps: "Brechas abiertas",
    activeArea: "Área activa",
    primary: "Primaria",
    secondary: "Secundaria",
    derived: "Derivada",
    aerialKicker: "Lectura aérea · +41 horas",
    aerialTitle: "¿Qué respuesta puede verse desde arriba?",
    aerialIntro: "Una revisión humana de los candidatos de vehículos, maquinaria y uso de sitio en la ortofoto Copernicus del 26 de junio.",
    reviewedCandidates: "Candidatos revisados",
    publishedSites: "Sitios publicados",
    likelyResponseSites: "Señales probables",
    identifiableShelters: "Refugios identificables",
    nativePixels: "Píxeles nativos",
    enhancedView: "Vista mejorada 2×",
    displayOnly: "Derivada · solo visualización",
    category: "Tipo de observación",
    status: "Estado de revisión",
    heavyMachinery: "Maquinaria",
    largeVehicles: "Vehículos grandes",
    siteUse: "Uso del sitio",
    likelyResponse: "Probable respuesta",
    unresolved: "No resuelto",
    openLocation: "Abrir ubicación",
    sourceHash: "Huella del original",
    modelAudit: "Auditoría de modelos",
    modelAuditIntro: "Solo la mejora 2× pasó la revisión, y únicamente como ayuda visual. Los detectores y la mejora 4× fueron rechazados.",
    acceptedDisplay: "Aceptado para visualización",
    rejected: "Rechazado",
    enhancementWarning: "La mejora no crea detalle real. Toda observación debe seguir siendo defendible en el chip nativo.",
    phase: {
      impact: "Impacto",
      "search-rescue": "Búsqueda y rescate",
      coordination: "Coordinación",
      logistics: "Logística",
      shelter: "Refugio",
      relief: "Asistencia",
      "debris-recovery": "Escombros",
      recovery: "Recuperación",
    } as Record<string, string>,
  },
  en: {
    reconstruction: "Public reconstruction · evidence in progress",
    title: "What happened after",
    openMap: "Open damage map",
    scope: "Scope",
    evidenceCutoff: "Latest evidence",
    sources: "Registered sources",
    events: "Reconstructed events",
    first72: "The first 72 hours",
    first72Kicker: "The critical question",
    first72Question: "When did help arrive — and when did it actually reach sites?",
    assessment: "Current assessment",
    evidenceRule: "How to read this conclusion",
    evidenceRuleText: "Announced, mobilized, arrived, observed and operational are different states. The atlas does not merge them.",
    filters: "Filter the timeline",
    all: "All",
    timeline: "Response timeline",
    timelineIntro: "Every entry separates observation from inference and links the sources supporting its description.",
    first72Only: "Within 72 h",
    after72: "After 72 h",
    evidence: "evidence",
    source: "source",
    sourcePlural: "sources",
    openSource: "Open source",
    sourceLedger: "Source ledger",
    sourceLedgerIntro: "Original material is linked. When reuse rights are unclear, the image or document is not copied.",
    method: "Method and limits",
    notObserved: "Not observed ≠ did not happen",
    arrivalStages: "Arrival is not one thing",
    imageEvidence: "Image evidence",
    imageCaveat: "Vehicle or machinery detections remain candidates until human review. One image cannot establish ownership, function, adequacy or movement.",
    latest: "Last updated",
    backToTop: "Back to top",
    present: "Presence",
    areaIndex: "Published reconstructions",
    areaIndexIntro: "Move between territories without changing the evidence rules.",
    officialRecord: "Official EMS record",
    confirmedDamage: "destroyed/damaged",
    possibleDamage: "possible",
    evidenceGaps: "Open gaps",
    activeArea: "Active area",
    primary: "Primary",
    secondary: "Secondary",
    derived: "Derived",
    aerialKicker: "Aerial reading · +41 hours",
    aerialTitle: "What response can be seen from above?",
    aerialIntro: "A human review of vehicle, machinery and site-use candidates in the June 26 Copernicus orthomosaic.",
    reviewedCandidates: "Candidates reviewed",
    publishedSites: "Published sites",
    likelyResponseSites: "Probable signals",
    identifiableShelters: "Identifiable shelters",
    nativePixels: "Native pixels",
    enhancedView: "Enhanced 2× view",
    displayOnly: "Derivative · display only",
    category: "Observation type",
    status: "Review status",
    heavyMachinery: "Machinery",
    largeVehicles: "Large vehicles",
    siteUse: "Site use",
    likelyResponse: "Likely response",
    unresolved: "Unresolved",
    openLocation: "Open location",
    sourceHash: "Source fingerprint",
    modelAudit: "Model audit",
    modelAuditIntro: "Only the 2× enhancement passed review, and only as a viewing aid. The detectors and 4× enhancement were rejected.",
    acceptedDisplay: "Accepted for display",
    rejected: "Rejected",
    enhancementWarning: "Enhancement does not create real detail. Every observation must remain supportable in the native chip.",
    phase: {
      impact: "Impact",
      "search-rescue": "Search & rescue",
      coordination: "Coordination",
      logistics: "Logistics",
      shelter: "Shelter",
      relief: "Relief",
      "debris-recovery": "Debris",
      recovery: "Recovery",
    } as Record<string, string>,
  },
};

const confidenceLabels: Record<Language, Record<ReconstructionConfidence, string>> = {
  es: {
    confirmed: "Confirmado",
    corroborated: "Corroborado",
    "single-source": "Una fuente",
    inferred: "Inferido",
  },
  en: {
    confirmed: "Confirmed",
    corroborated: "Corroborated",
    "single-source": "Single source",
    inferred: "Inferred",
  },
};

const stageLabels: Record<Language, Record<ResponseStage, string>> = {
  es: {
    impact: "Impacto",
    announced: "Anunciado",
    reported: "Reportado",
    mobilized: "Movilizado",
    "arrived-country": "Llegó al país",
    "arrived-region": "Llegó a la región",
    "observed-site": "Observado en sitio",
    operational: "Operativo",
    assessment: "Evaluación",
    recovery: "Recuperación",
  },
  en: {
    impact: "Impact",
    announced: "Announced",
    reported: "Reported",
    mobilized: "Mobilized",
    "arrived-country": "Arrived in country",
    "arrived-region": "Arrived in region",
    "observed-site": "Observed at site",
    operational: "Operational",
    assessment: "Assessment",
    recovery: "Recovery",
  },
};

function formatDate(value: string, language: Language, precision: ReconstructionEvent["timePrecision"] = "day") {
  const date = new Date(value);
  return new Intl.DateTimeFormat(language === "es" ? "es-VE" : "en-US", {
    timeZone: "America/Caracas",
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(precision === "minute" || precision === "second"
      ? { hour: "2-digit", minute: "2-digit", hour12: false }
      : {}),
  }).format(date);
}

function formatCompactDate(value: string, language: Language) {
  return new Intl.DateTimeFormat(language === "es" ? "es-VE" : "en-US", {
    timeZone: "America/Caracas",
    day: "numeric",
    month: "short",
  }).format(new Date(value));
}

function hourOffset(origin: string, value: string) {
  return Math.max(0, Math.round((new Date(value).getTime() - new Date(origin).getTime()) / 3_600_000));
}

function SourceLinks({
  ids,
  sourcesById,
}: {
  ids: string[];
  sourcesById: Map<string, ReconstructionSource>;
}) {
  return (
    <div className={styles.sourceLinks}>
      {ids.map((id, index) => {
        const source = sourcesById.get(id);
        if (!source) return null;
        return (
          <a key={id} href={source.url} target="_blank" rel="noreferrer">
            <span>{String(index + 1).padStart(2, "0")}</span>
            {source.publisher}
          </a>
        );
      })}
    </div>
  );
}

function EvidenceImage({
  finding,
  language,
}: {
  finding: First72Finding | ReconstructionEvent;
  language: Language;
}) {
  if (!finding.image) return null;
  return (
    <figure className={styles.evidenceFigure}>
      <Image
        src={finding.image.src}
        width={1024}
        height={548}
        unoptimized
        sizes="(max-width: 760px) 100vw, 760px"
        alt={finding.image.alt[language]}
      />
      <figcaption>{finding.image.caption[language]}</figcaption>
    </figure>
  );
}

function AerialEvidenceExplorer({
  evidence,
  language,
}: {
  evidence: AerialEvidenceCollection;
  language: Language;
}) {
  const t = copy[language];
  const [category, setCategory] = useState<"all" | "heavy-machinery" | "large-vehicles" | "site-use">("all");
  const [status, setStatus] = useState<"all" | "likely-response-related" | "unresolved">("all");
  const [imageMode, setImageMode] = useState<"native" | "enhanced">("native");
  const observations = evidence.observations.filter((observation) => {
    if (category !== "all" && observation.category !== category) return false;
    if (status !== "all" && observation.status !== status) return false;
    return true;
  });
  const categoryLabels = {
    "heavy-machinery": t.heavyMachinery,
    "large-vehicles": t.largeVehicles,
    "site-use": t.siteUse,
  };

  return (
    <section className={styles.aerialSection} id="aerial-evidence">
      <div className={styles.aerialHeader}>
        <div className={styles.sectionHeading}>
          <p>{t.aerialKicker}</p>
          <h2>{t.aerialTitle}</h2>
        </div>
        <p>{t.aerialIntro}</p>
      </div>

      <div className={styles.aerialSummary}>
        <dl>
          <div>
            <dt>{t.reviewedCandidates}</dt>
            <dd>{evidence.review.candidateRecords}</dd>
          </div>
          <div>
            <dt>{t.publishedSites}</dt>
            <dd>{evidence.review.publishedSites}</dd>
          </div>
          <div>
            <dt>{t.likelyResponseSites}</dt>
            <dd>{evidence.review.likelyResponseSites}</dd>
          </div>
          <div>
            <dt>{t.identifiableShelters}</dt>
            <dd>{evidence.review.confidentSheltersOrSleepingSites}</dd>
          </div>
        </dl>
        <div>
          <p>{evidence.review.summary[language]}</p>
          <small>{evidence.review.absenceCaveat[language]}</small>
        </div>
      </div>

      <div className={styles.aerialControls}>
        <div>
          <p>{t.category}</p>
          <div className={styles.filterRow}>
            <button type="button" aria-pressed={category === "all"} onClick={() => setCategory("all")}>{t.all}</button>
            <button type="button" aria-pressed={category === "heavy-machinery"} onClick={() => setCategory("heavy-machinery")}>{t.heavyMachinery}</button>
            <button type="button" aria-pressed={category === "large-vehicles"} onClick={() => setCategory("large-vehicles")}>{t.largeVehicles}</button>
            <button type="button" aria-pressed={category === "site-use"} onClick={() => setCategory("site-use")}>{t.siteUse}</button>
          </div>
        </div>
        <div>
          <p>{t.status}</p>
          <div className={styles.filterRow}>
            <button type="button" aria-pressed={status === "all"} onClick={() => setStatus("all")}>{t.all}</button>
            <button type="button" aria-pressed={status === "likely-response-related"} onClick={() => setStatus("likely-response-related")}>{t.likelyResponse}</button>
            <button type="button" aria-pressed={status === "unresolved"} onClick={() => setStatus("unresolved")}>{t.unresolved}</button>
          </div>
        </div>
        <div>
          <p>{language === "es" ? "Imagen" : "Image"}</p>
          <div className={styles.filterRow}>
            <button type="button" aria-pressed={imageMode === "native"} onClick={() => setImageMode("native")}>{t.nativePixels}</button>
            <button type="button" aria-pressed={imageMode === "enhanced"} onClick={() => setImageMode("enhanced")}>{t.enhancedView}</button>
          </div>
        </div>
      </div>

      {imageMode === "enhanced" && (
        <aside className={styles.enhancementWarning}>
          <span>AI / 2×</span>
          <p>{t.enhancementWarning}</p>
        </aside>
      )}

      <div className={styles.aerialGrid}>
        {observations.map((observation) => {
          const isEnhanced = imageMode === "enhanced";
          const image = isEnhanced ? observation.enhancedImage : observation.nativeImage;
          return (
            <article key={observation.id} className={styles.aerialCard}>
              <figure>
                <Image
                  src={image}
                  width={isEnhanced ? 1024 : 512}
                  height={isEnhanced ? 1024 : 512}
                  unoptimized
                  sizes="(max-width: 720px) 100vw, 50vw"
                  alt={`${observation.title[language]} · ${isEnhanced ? t.enhancedView : t.nativePixels}`}
                />
                <figcaption>
                  <span>{isEnhanced ? t.displayOnly : t.nativePixels}</span>
                  <small>{observation.chipId}</small>
                </figcaption>
              </figure>
              <div className={styles.aerialCardBody}>
                <div className={styles.badgeRow}>
                  <span className={`${styles.confidence} ${styles[observation.confidence]}`}>
                    {confidenceLabels[language][observation.confidence]}
                  </span>
                  <span className={styles.stage}>
                    {observation.status === "likely-response-related" ? t.likelyResponse : t.unresolved}
                  </span>
                  <span className={styles.phase}>{categoryLabels[observation.category]}</span>
                </div>
                <h3>{observation.title[language]}</h3>
                <p>{observation.finding[language]}</p>
                <div className={styles.aerialMeta}>
                  <span>{observation.location.label}</span>
                  <small>{t.sourceHash}: {observation.nativeSha256.slice(0, 12)}…</small>
                </div>
                <a href={observation.mapUrl} target="_blank" rel="noreferrer">
                  {t.openLocation} ↗
                </a>
              </div>
            </article>
          );
        })}
      </div>

      <details className={styles.modelAudit}>
        <summary>{t.modelAudit}</summary>
        <p>{t.modelAuditIntro}</p>
        <div>
          {evidence.modelBenchmarks.map((benchmark) => (
            <article key={benchmark.modelId}>
              <span>{benchmark.result === "accepted-display-only" ? t.acceptedDisplay : t.rejected}</span>
              <h3>{benchmark.modelId}</h3>
              <p>{benchmark.note[language]}</p>
            </article>
          ))}
        </div>
      </details>
    </section>
  );
}

export default function TimelineExplorer({
  data,
  catalog,
  activeSlug,
}: {
  data: ReconstructionData;
  catalog: ReconstructionCatalog;
  activeSlug: string;
}) {
  const language = useSyncExternalStore(subscribeStoredLang, readStoredLang, () => DEFAULT_LANGUAGE);
  const [phase, setPhase] = useState("all");
  const [windowFilter, setWindowFilter] = useState<"all" | "first72" | "after72">("all");
  const t = copy[language];
  const sourceMap = useMemo(() => new Map(data.sources.map((source) => [source.id, source])), [data.sources]);
  const phases = useMemo(
    () => Array.from(new Set(data.events.map((event) => event.phase))),
    [data.events],
  );
  const filteredEvents = useMemo(
    () =>
      data.events.filter((event) => {
        if (phase !== "all" && event.phase !== phase) return false;
        if (windowFilter === "first72" && !event.first72Hours) return false;
        if (windowFilter === "after72" && event.first72Hours) return false;
        return true;
      }),
    [data.events, phase, windowFilter],
  );

  const changeLanguage = (nextLanguage: Language) => {
    persistLang(nextLanguage);
    document.documentElement.lang = nextLanguage;
  };

  const heroImage = data.events.find((event) => event.id === "copernicus-41-hour-image")?.image;
  const resolvedHeroImage = heroImage ?? data.events.find((event) => event.image)?.image;
  const activeEntry = catalog.entries.find((entry) => entry.slug === activeSlug);
  const heroDek = language === "es"
    ? `Una reconstrucción fechada y verificable de los terremotos del 24 de junio y su respuesta en ${data.coverage.geography.es}.`
    : `A dated, verifiable reconstruction of the June 24 earthquakes and the response in ${data.coverage.geography.en}.`;

  return (
    <main className={styles.page} id="top">
      <nav className={styles.topbar} aria-label={language === "es" ? "Navegación principal" : "Main navigation"}>
        <Link href="/" className={styles.wordmark}>
          <span>RV</span>
          <b>Respuesta Venezuela</b>
        </Link>
        <div className={styles.topActions}>
          <div className={styles.languageSwitch} aria-label={language === "es" ? "Idioma" : "Language"}>
            <button type="button" onClick={() => changeLanguage("es")} aria-pressed={language === "es"}>ES</button>
            <button type="button" onClick={() => changeLanguage("en")} aria-pressed={language === "en"}>EN</button>
          </div>
          <Link href="/" className={styles.mapLink}>{t.openMap}</Link>
        </div>
      </nav>

      <section className={styles.areaIndex} aria-labelledby="reconstruction-area-title">
        <div className={styles.areaIndexHeading}>
          <div>
            <p>{t.areaIndex}</p>
            <h2 id="reconstruction-area-title">{t.areaIndexIntro}</h2>
          </div>
          <span>{catalog.entries.filter((entry) => entry.status === "published").length}</span>
        </div>
        <div className={styles.areaCards}>
          {catalog.entries.filter((entry) => entry.status === "published").map((entry) => {
            const isActive = entry.slug === activeSlug;
            const href = entry.slug === catalog.defaultSlug ? "/timeline" : `/timeline/${entry.slug}`;
            return (
              <Link
                key={entry.id}
                href={href}
                className={`${styles.areaCard} ${isActive ? styles.areaCardActive : ""}`}
                aria-current={isActive ? "page" : undefined}
              >
                <span>{String(entry.priority).padStart(2, "0")}</span>
                <div>
                  <small>{isActive ? t.activeArea : t.officialRecord}</small>
                  <h3>{entry.geography[language]}</h3>
                  <p>{entry.description[language]}</p>
                  <dl>
                    <div>
                      <dt>{t.confirmedDamage}</dt>
                      <dd>{entry.officialDamage.damagedConfirmed}</dd>
                    </div>
                    <div>
                      <dt>{t.possibleDamage}</dt>
                      <dd>{entry.officialDamage.possibleDamage}</dd>
                    </div>
                    <div>
                      <dt>{t.evidenceGaps}</dt>
                      <dd>{entry.gaps.length}</dd>
                    </div>
                  </dl>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <header className={styles.hero}>
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}>{t.reconstruction}</p>
          <h1>{t.title}</h1>
          <p className={styles.dek}>{heroDek}</p>
          <dl className={styles.heroStats}>
            <div>
              <dt>{t.scope}</dt>
              <dd>{data.coverage.geography[language]}</dd>
            </div>
            <div>
              <dt>{t.evidenceCutoff}</dt>
              <dd>{formatDate(data.coverage.latestEvidenceAt, language)}</dd>
            </div>
            <div>
              <dt>{t.events}</dt>
              <dd>{data.events.length}</dd>
            </div>
            <div>
              <dt>{t.sources}</dt>
              <dd>{data.sources.length}</dd>
            </div>
          </dl>
        </div>

        {resolvedHeroImage && (
          <figure className={styles.heroImage}>
            <Image
              src={resolvedHeroImage.src}
              width={1024}
              height={548}
              priority
              unoptimized
              sizes="(max-width: 900px) 100vw, 54vw"
              alt={resolvedHeroImage.alt[language]}
            />
            <figcaption>
              <span>{activeSlug === "la-guaira" ? "+41 h" : "+22 h"}</span>
              {resolvedHeroImage.caption[language]}
            </figcaption>
          </figure>
        )}
      </header>

      <section className={styles.coverageNote} aria-label={language === "es" ? "Límite de cobertura" : "Coverage limit"}>
        <span>01</span>
        <div>
          <p>{data.coverage.note[language]}</p>
          {activeEntry && (
            <ul className={styles.gapList} aria-label={t.evidenceGaps}>
              {activeEntry.gaps.map((gap) => <li key={gap.en}>{gap[language]}</li>)}
            </ul>
          )}
        </div>
      </section>

      <section className={styles.first72} id="first-72">
        <div className={styles.sectionHeading}>
          <p>{t.first72Kicker}</p>
          <h2>{t.first72Question}</h2>
        </div>

        <div className={styles.horizon} aria-label={t.first72}>
          <div className={styles.horizonRail}>
            <span style={{ left: "0%" }}>0 h</span>
            <span style={{ left: "33.33%" }}>24 h</span>
            <span style={{ left: "66.66%" }}>48 h</span>
            <span style={{ left: "100%" }}>72 h</span>
          </div>
          <div className={styles.horizonTicks}>
            {data.events.filter((event) => event.first72Hours).map((event) => {
              const offset = Math.min(72, hourOffset(data.eventOrigin, event.startsAt));
              return (
                <a
                  key={event.id}
                  href={`#event-${event.id}`}
                  style={{ left: `${(offset / 72) * 100}%` }}
                  title={`${event.title[language]} · +${offset} h`}
                >
                  <span className="sr-only">{event.title[language]}</span>
                </a>
              );
            })}
          </div>
        </div>

        <article className={styles.assessment}>
          <div>
            <p className={styles.monoLabel}>{t.assessment}</p>
            <h3>{data.first72Assessment.headline[language]}</h3>
          </div>
          <p>{data.first72Assessment.summary[language]}</p>
        </article>

        <div className={styles.findings}>
          {data.first72Assessment.findings.map((finding, index) => (
            <article key={finding.id} className={styles.finding}>
              <div className={styles.findingIndex}>{String(index + 1).padStart(2, "0")}</div>
              <div>
                <div className={styles.badgeRow}>
                  <span className={`${styles.confidence} ${styles[finding.confidence]}`}>
                    {confidenceLabels[language][finding.confidence]}
                  </span>
                  <span className={styles.stage}>{stageLabels[language][finding.status]}</span>
                </div>
                <h3>{finding.title[language]}</h3>
                <p>{finding.body[language]}</p>
                <SourceLinks ids={finding.sourceIds} sourcesById={sourceMap} />
              </div>
              <EvidenceImage finding={finding} language={language} />
            </article>
          ))}
        </div>

        <aside className={styles.readingRule}>
          <div>
            <span>!</span>
            <b>{t.evidenceRule}</b>
          </div>
          <p>{t.evidenceRuleText}</p>
        </aside>
      </section>

      {data.aerialEvidence && (
        <AerialEvidenceExplorer evidence={data.aerialEvidence} language={language} />
      )}

      <section className={styles.timelineSection} id="timeline">
        <div className={styles.timelineHeader}>
          <div className={styles.sectionHeading}>
            <p>{t.timeline}</p>
            <h2>{t.timelineIntro}</h2>
          </div>
          <div className={styles.filterPanel}>
            <p>{t.filters}</p>
            <div className={styles.filterRow}>
              <button type="button" aria-pressed={phase === "all"} onClick={() => setPhase("all")}>{t.all}</button>
              {phases.map((item) => (
                <button key={item} type="button" aria-pressed={phase === item} onClick={() => setPhase(item)}>
                  {t.phase[item] ?? item}
                </button>
              ))}
            </div>
            <div className={styles.filterRow}>
              <button type="button" aria-pressed={windowFilter === "all"} onClick={() => setWindowFilter("all")}>{t.all}</button>
              <button type="button" aria-pressed={windowFilter === "first72"} onClick={() => setWindowFilter("first72")}>{t.first72Only}</button>
              <button type="button" aria-pressed={windowFilter === "after72"} onClick={() => setWindowFilter("after72")}>{t.after72}</button>
            </div>
          </div>
        </div>

        <div className={styles.timeline}>
          {filteredEvents.map((event, index) => {
            const offset = hourOffset(data.eventOrigin, event.startsAt);
            return (
              <article key={event.id} className={styles.event} id={`event-${event.id}`}>
                <div className={styles.eventDate}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <time dateTime={event.startsAt}>{formatDate(event.startsAt, language, event.timePrecision)}</time>
                  <small>+{offset} h</small>
                </div>
                <div className={styles.eventBody}>
                  <div className={styles.badgeRow}>
                    <span className={styles.phase}>{t.phase[event.phase] ?? event.phase}</span>
                    <span className={`${styles.confidence} ${styles[event.confidence]}`}>
                      {confidenceLabels[language][event.confidence]}
                    </span>
                    <span className={styles.stage}>{stageLabels[language][event.responseStage]}</span>
                  </div>
                  <h3>{event.title[language]}</h3>
                  <p>{event.summary[language]}</p>
                  <div className={styles.locationLine}>
                    <span>{event.location.label}</span>
                    <small>{event.location.precision}</small>
                  </div>
                  <SourceLinks ids={event.sourceIds} sourcesById={sourceMap} />
                  <EvidenceImage finding={event} language={language} />
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className={styles.methodSection} id="method">
        <div className={styles.sectionHeading}>
          <p>{t.method}</p>
          <h2>{language === "es" ? "Una afirmación tan fuerte como su evidencia." : "A claim only as strong as its evidence."}</h2>
        </div>
        <div className={styles.methodGrid}>
          <article>
            <span>01</span>
            <h3>{t.notObserved}</h3>
            <p>{data.method.absenceRule[language]}</p>
          </article>
          <article>
            <span>02</span>
            <h3>{t.arrivalStages}</h3>
            <p>{data.method.arrivalRule[language]}</p>
          </article>
          <article>
            <span>03</span>
            <h3>{t.imageEvidence}</h3>
            <p>{t.imageCaveat}</p>
          </article>
        </div>
        <div className={styles.confidenceGrid}>
          {data.method.confidenceLevels.map((level) => (
            <article key={level.id}>
              <span className={`${styles.confidence} ${styles[level.id]}`}>{level.label[language]}</span>
              <p>{level.definition[language]}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.sourcesSection} id="sources">
        <div className={styles.sectionHeading}>
          <p>{t.sourceLedger}</p>
          <h2>{t.sourceLedgerIntro}</h2>
        </div>
        <div className={styles.sourceLedger}>
          {data.sources.map((source, index) => (
            <article key={source.id}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div>
                <p>{source.publisher}</p>
                <h3>{source.title}</h3>
                <small>
                  {formatCompactDate(source.publishedAt, language)} · {source.type} · {t[source.evidenceClass]}
                </small>
              </div>
              <a href={source.url} target="_blank" rel="noreferrer">
                {t.openSource}
                <span aria-hidden="true">↗</span>
              </a>
            </article>
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        <div>
          <span>RV / 2026</span>
          <p>{data.coverage.geography[language]}</p>
        </div>
        <p>{t.latest}: {formatDate(data.updatedAt, language, "minute")}</p>
        <a href="#top">{t.backToTop} ↑</a>
      </footer>
    </main>
  );
}
