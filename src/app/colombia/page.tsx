import type { Metadata } from "next";
import Link from "next/link";
import incident from "../../../public/data/incidents/colombia-2026-08-10-san-jose-del-palmar.json";
import styles from "./colombia.module.css";

type Bilingual = {
  es: string;
  en: string;
};

const registryHref = "/data/incidents/colombia-2026-08-10-san-jose-del-palmar.json";
const externalLinkProps = {
  target: "_blank",
  rel: "noreferrer noopener",
} as const;

export const metadata: Metadata = {
  title: "Colombia · Boletín de activación | Respuesta",
  description:
    "Boletín público bilingüe de activación y verificación para el sismo de San José del Palmar, Chocó.",
  alternates: {
    canonical: "/colombia",
  },
  openGraph: {
    type: "website",
    url: "/colombia",
    title: "Colombia · Boletín de activación",
    description:
      "Hechos verificados, estado de tsunami, vacíos de información y prioridades operativas para San José del Palmar, Chocó.",
  },
};

function colombiaTimestamp(value: string, locale: "es-CO" | "en-US") {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Bogota",
  }).format(new Date(value));
}

function BilingualText({ value }: { value: Bilingual }) {
  return (
    <>
      <span>{value.es}</span>
      <span className={styles.english} lang="en">
        {value.en}
      </span>
    </>
  );
}

function SituationCard({
  id,
  title,
  items,
  tone,
}: {
  id: string;
  title: Bilingual;
  items: Array<{ es: string; en: string }>;
  tone: "known" | "unconfirmed" | "unknown";
}) {
  return (
    <article className={`${styles.situationCard} ${styles[tone]}`} aria-labelledby={id}>
      <h3 id={id}>
        <BilingualText value={title} />
      </h3>
      <ul>
        {items.map((item) => (
          <li key={item.es}>
            <BilingualText value={item} />
          </li>
        ))}
      </ul>
    </article>
  );
}

export default function ColombiaPage() {
  const verifiedEs = colombiaTimestamp(incident.lastVerifiedAt, "es-CO");
  const verifiedEn = colombiaTimestamp(incident.lastVerifiedAt, "en-US");

  return (
    <main
      className={styles.page}
      data-incident-id={incident.incidentId}
      data-status={incident.status}
      id="contenido"
    >
      <a className={styles.skipLink} href="#hechos">
        Saltar al contenido / <span lang="en">Skip to content</span>
      </a>

      <header className={styles.hero}>
        <nav className={styles.topNav} aria-label="Incidentes y datos / Incidents and data">
          <Link href="/" className={styles.backLink}>
            <span aria-hidden="true">←</span> Venezuela · incidente preservado
          </Link>
          <a className={styles.registryLink} href={registryHref}>
            Registro JSON / <span lang="en">JSON registry</span>
          </a>
        </nav>

        <div className={styles.eyebrowRow}>
          <p className={styles.eyebrow}>RESPUESTA · COLOMBIA</p>
          <span className={styles.activationPill}>{incident.statusLabel.es}</span>
        </div>

        <h1>{incident.event.title.es}</h1>
        <p className={styles.heroEnglish} lang="en">
          {incident.event.title.en}
        </p>

        <div className={styles.verificationBar}>
          <div>
            <strong>Última verificación</strong>
            <span>{verifiedEs} · hora de Colombia</span>
          </div>
          <div lang="en">
            <strong>Last verified</strong>
            <span>{verifiedEn} · Colombia time</span>
          </div>
          <code>{incident.incidentId}</code>
        </div>

        <p className={styles.scope}>
          <BilingualText value={incident.verificationScope} />
        </p>
      </header>

      <section className={styles.section} aria-labelledby="hechos-titulo" id="hechos">
        <div className={styles.sectionHeading}>
          <p>01 · EVENTO / EVENT</p>
          <h2 id="hechos-titulo">Hechos sísmicos verificados</h2>
          <span lang="en">Verified earthquake facts</span>
        </div>

        <dl className={styles.facts}>
          <div>
            <dt>Magnitud <span lang="en">/ Magnitude</span></dt>
            <dd>{incident.event.magnitude}</dd>
          </div>
          <div>
            <dt>Origen local <span lang="en">/ Local origin</span></dt>
            <dd>
              <time dateTime={incident.event.originLocal}>
                10 ago 2026 · 07:34 COT
              </time>
            </dd>
          </div>
          <div>
            <dt>Profundidad <span lang="en">/ Depth</span></dt>
            <dd className={styles.depthValues}>
              <span>{incident.event.depthKm} km <small>Visor SGC · DIMAR</small></span>
              <span>{incident.event.depthContext.officialAlternativeKm} km <small>Comunicado SGC / <span lang="en">SGC statement</span></small></span>
            </dd>
          </div>
          <div>
            <dt>Coordenadas <span lang="en">/ Coordinates</span></dt>
            <dd>{incident.event.latitude}°, {incident.event.longitude}°</dd>
          </div>
          <div className={styles.wideFact}>
            <dt>Referencia <span lang="en">/ Reference</span></dt>
            <dd>
              <BilingualText value={incident.event.reference} />
            </dd>
          </div>
          <div>
            <dt>ID del evento SGC <span lang="en">/ SGC event ID</span></dt>
            <dd><code>{incident.event.sourceEventId}</code></dd>
          </div>
        </dl>
      </section>

      <section className={styles.tsunamiStatus} aria-labelledby="tsunami">
        <div className={styles.statusMark} aria-hidden="true">✓</div>
        <div>
          <p className={styles.statusLabel}>ESTADO OFICIAL · TSUNAMI</p>
          <h2 id="tsunami">No existe amenaza de tsunami</h2>
          <p>{incident.tsunami.summary.es}</p>
          <p lang="en">{incident.tsunami.summary.en}</p>
          <small>
            DIMAR · Boletín informativo No. 01 ·{" "}
            <time dateTime={incident.tsunami.issuedAt}>10 ago 2026, 08:04 COT</time>
          </small>
        </div>
      </section>

      <section className={styles.damageHold} aria-labelledby="capa-danos">
        <div>
          <p className={styles.statusLabel}>MAPA / MAP</p>
          <h2 id="capa-danos">Capa de daños en espera</h2>
          <p lang="en">Damage layer on hold</p>
        </div>
        <div>
          <p>{incident.publicDamageLayer.summary.es}</p>
          <p lang="en">{incident.publicDamageLayer.summary.en}</p>
          <p className={styles.holdRule}>
            Los AOI se abrirán únicamente con una fuente, fecha, licencia y alcance de verificación identificables.
            <span lang="en"> AOIs will open only with an identifiable source, date, license, and verification scope.</span>
          </p>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="situacion">
        <div className={styles.sectionHeading}>
          <p>02 · SITUACIÓN / SITUATION</p>
          <h2 id="situacion">Lo que podemos afirmar ahora</h2>
          <span lang="en">What we can say now</span>
        </div>
        <div className={styles.situationGrid}>
          <SituationCard
            id="conocido"
            title={{ es: "Conocido", en: "Known" }}
            items={incident.situation.known}
            tone="known"
          />
          <SituationCard
            id="sin-confirmar"
            title={{ es: "Sin confirmar", en: "Unconfirmed" }}
            items={incident.situation.unconfirmed}
            tone="unconfirmed"
          />
          <SituationCard
            id="desconocido"
            title={{ es: "Desconocido", en: "Unknown" }}
            items={incident.situation.unknown}
            tone="unknown"
          />
        </div>
      </section>

      <section className={styles.splitSection}>
        <div aria-labelledby="seguridad">
          <div className={styles.sectionHeading}>
            <p>03 · SEGURIDAD / SAFETY</p>
            <h2 id="seguridad">Réplicas y acceso seguro</h2>
            <span lang="en">Aftershocks and safe access</span>
          </div>
          <ul className={styles.actionList}>
            {incident.safety.map((item) => (
              <li key={item.es}>
                <BilingualText value={item} />
              </li>
            ))}
          </ul>
        </div>

        <div aria-labelledby="prioridades">
          <div className={styles.sectionHeading}>
            <p>04 · OPERACIÓN / OPERATIONS</p>
            <h2 id="prioridades">Siguientes prioridades</h2>
            <span lang="en">Next priorities</span>
          </div>
          <ol className={styles.priorityList}>
            {incident.operationalPriorities.map((priority, index) => (
              <li key={priority.id}>
                <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>
                    {priority.title.es}
                    <span lang="en"> / {priority.title.en}</span>
                  </strong>
                  <p>{priority.detail.es}</p>
                  <p lang="en">{priority.detail.en}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className={styles.sources} aria-labelledby="fuentes">
        <div className={styles.sectionHeading}>
          <p>05 · EVIDENCIA / EVIDENCE</p>
          <h2 id="fuentes">Fuentes y política de publicación</h2>
          <span lang="en">Sources and publication policy</span>
        </div>

        <div className={styles.policy}>
          <p>{incident.sourcePolicy.es}</p>
          <p lang="en">{incident.sourcePolicy.en}</p>
        </div>

        <ul className={styles.sourceList}>
          {incident.sources.map((source) => (
            <li key={source.id}>
              <a className={styles.sourceLink} href={source.url} {...externalLinkProps}>
                <span>
                  {source.label.es}
                  <small lang="en">{source.label.en}</small>
                </span>
                <span aria-hidden="true">↗</span>
              </a>
              <span className={styles.sourceClass}>
                {source.authority === "official-colombia"
                  ? "Oficial Colombia / Official Colombia"
                  : "Contexto externo / External context"}
              </span>
            </li>
          ))}
        </ul>

        <div className={styles.registryCallout}>
          <div>
            <strong>Registro público verificable</strong>
            <span lang="en">Public verifiable registry</span>
          </div>
          <a href={registryHref}>Abrir JSON / <span lang="en">Open JSON</span></a>
        </div>
      </section>

      <footer className={styles.footer}>
        <p>
          {incident.updatePolicy.es}
          <span lang="en">{incident.updatePolicy.en}</span>
        </p>
        <Link href="/" className={styles.backLink}>
          <span aria-hidden="true">←</span> Volver a Venezuela / <span lang="en">Return to Venezuela</span>
        </Link>
      </footer>
    </main>
  );
}
