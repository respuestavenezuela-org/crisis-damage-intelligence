import type { Language } from "@/components/types";

export type LocalizedText = Record<Language, string>;
export type ReconstructionConfidence = "confirmed" | "corroborated" | "single-source" | "inferred";
export type ResponseStage =
  | "impact"
  | "announced"
  | "reported"
  | "mobilized"
  | "arrived-country"
  | "arrived-region"
  | "observed-site"
  | "operational"
  | "assessment"
  | "recovery";

export type ReconstructionImage = {
  src: string;
  alt: LocalizedText;
  caption: LocalizedText;
};

export type AerialEvidenceObservation = {
  id: string;
  chipId: string;
  status: "likely-response-related" | "unresolved";
  confidence: ReconstructionConfidence;
  category: "heavy-machinery" | "large-vehicles" | "site-use";
  location: {
    label: string;
    latitude: number;
    longitude: number;
    precision: string;
  };
  title: LocalizedText;
  finding: LocalizedText;
  nativeImage: string;
  enhancedImage: string;
  nativeSha256: string;
  enhancedSha256: string;
  mapUrl: string;
  sourceIds: string[];
  temporalFollowup: {
    acquisitionAt: string;
    hoursAfterEvent: number;
    sourceId: string;
    sensor: string;
    sourceRole: "external-triage";
    reviewStatus:
      | "weakens-response-attribution"
      | "supports-object-persistence"
      | "not-discernible-in-followup";
    nativeImage: string;
    enhancedImage: string;
    compareImage: string;
    nativeSha256: string;
    enhancedSha256: string;
    compareSha256: string;
    finding: LocalizedText;
    limitations: LocalizedText;
  };
};

export type AerialEvidenceCollection = {
  version: number;
  id: string;
  updatedAt: string;
  aoiId: string;
  acquisitionAt: string;
  hoursAfterEvent: number;
  sourceId: string;
  source: {
    publisher: string;
    sensor: string;
    product: string;
    url: string;
    license: string;
  };
  inventory: {
    url: string;
    checkedAt: string;
    officialAois: number;
    localOpticalAois: number;
    opticalProductRecords: number;
    distinctOpticalAcquisitions: number;
    publiclyReadableOpticalCogs: number;
    readableOpticalBytes: number;
    countingNote: LocalizedText;
  };
  temporalReview: {
    status: "human-reviewed";
    summary: LocalizedText;
    officialJuly5: {
      acquisitionAt: string;
      sensor: string;
      sourceId: string;
      candidateLocationsChecked: number;
      publishedSitesChecked: number;
      publishedSitesUsableForObjectComparison: number;
      finding: LocalizedText;
    };
    externalFollowup: {
      sourceIds: string[];
      publishedSitesChecked: number;
      usableComparisons: number;
      acquisitionDates: string[];
      finding: LocalizedText;
    };
  };
  review: {
    method: LocalizedText;
    summary: LocalizedText;
    absenceCaveat: LocalizedText;
    candidateRecords: number;
    publishedSites: number;
    likelyResponseSites: number;
    unresolvedSites: number;
    confidentCollectionCentres: number;
    confidentSheltersOrSleepingSites: number;
    candidateIds: string[];
  };
  enhancement: {
    status: "display-only";
    modelId: string;
    modelRevision: string;
    scale: number;
    license: string;
    method: LocalizedText;
    acceptanceRule: LocalizedText;
  };
  modelBenchmarks: Array<{
    modelId: string;
    revision: string;
    task: string;
    result: "accepted-display-only" | "rejected";
    note: LocalizedText;
  }>;
  observations: AerialEvidenceObservation[];
};

export type ReconstructionSource = {
  id: string;
  publisher: string;
  title: string;
  publishedAt: string;
  url: string;
  type: string;
  evidenceClass: "primary" | "secondary" | "derived";
  license: string;
};

export type ReconstructionEvent = {
  id: string;
  startsAt: string;
  endsAt?: string;
  timePrecision: "second" | "minute" | "day" | "range";
  phase: string;
  responseStage: ResponseStage;
  first72Hours: boolean;
  confidence: ReconstructionConfidence;
  location: {
    label: string;
    precision: string;
  };
  title: LocalizedText;
  summary: LocalizedText;
  sourceIds: string[];
  tags: string[];
  image?: ReconstructionImage;
};

export type First72Finding = {
  id: string;
  status: ResponseStage;
  confidence: ReconstructionConfidence;
  title: LocalizedText;
  body: LocalizedText;
  sourceIds: string[];
  image?: ReconstructionImage;
};

export type ReconstructionData = {
  version: number;
  id: string;
  updatedAt: string;
  eventOrigin: string;
  coverage: {
    geography: LocalizedText;
    startsAt: string;
    endsAt: string;
    latestEvidenceAt: string;
    latestOpenSatelliteAt: string;
    note: LocalizedText;
  };
  method: {
    confidenceLevels: Array<{
      id: ReconstructionConfidence;
      label: LocalizedText;
      definition: LocalizedText;
    }>;
    absenceRule: LocalizedText;
    arrivalRule: LocalizedText;
  };
  first72Assessment: {
    cutoff: string;
    headline: LocalizedText;
    summary: LocalizedText;
    findings: First72Finding[];
  };
  aerialEvidence?: AerialEvidenceCollection;
  sources: ReconstructionSource[];
  events: ReconstructionEvent[];
};

export type ReconstructionCatalogEntry = {
  id: string;
  slug: string;
  dataPath: string;
  status: "published" | "developing" | "queued";
  priority: number;
  geography: LocalizedText;
  description: LocalizedText;
  updatedAt: string;
  evidenceCutoff: string;
  eventCount: number;
  sourceCount: number;
  imageEventCount: number;
  officialDamage: {
    destroyed: number;
    damagedConfirmed: number;
    possibleDamage: number;
  };
  gaps: LocalizedText[];
};

export type ReconstructionCatalog = {
  version: number;
  updatedAt: string;
  defaultSlug: string;
  entries: ReconstructionCatalogEntry[];
};
