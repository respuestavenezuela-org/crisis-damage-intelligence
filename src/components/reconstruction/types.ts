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
