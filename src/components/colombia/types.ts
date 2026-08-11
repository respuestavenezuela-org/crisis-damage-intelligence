export type ColombiaLanguage = "es" | "en";

export type BilingualLabel = {
  es: string;
  en: string;
};

export type ColombiaImageryLayer = {
  role: "before" | "after";
  urlTemplate: string;
  minZoom: number;
  maxZoom: number;
  source: string;
  attribution: string;
  acquisitionUtc: string;
  license: string;
  limitations: BilingualLabel;
};

export type ColombiaReferenceLayer = {
  role: "visual-reference-only";
  urlTemplate: string;
  minZoom: number;
  maxZoom: number;
  source: string;
  attribution: string;
  limitations: BilingualLabel;
};

export type ColombiaMappingImage = {
  uuid: string;
  sensorType: "optical" | "sar" | string;
  sensor: string;
  resolutionClass: string;
  acquisitionUtc: string;
  fileName: string | null;
};

export type ColombiaMappingProduct = {
  id: number;
  type: "GRA" | "GRM" | string;
  typeLabel: BilingualLabel;
  monitoring: boolean;
  feasible: boolean;
  expectedDeliveryUtc: string | null;
  statusCode: string;
  status: "waiting" | "ready" | string;
  deliveryUtc: string | null;
  downloadPath: string | null;
  images: ColombiaMappingImage[];
};

export type ColombiaMappingAoi = {
  id: string;
  number: number;
  name: BilingualLabel;
  extentWkt: string;
  blpUrl: string | null;
  products: ColombiaMappingProduct[];
};

export type ColombiaMappingSnapshot = {
  schemaVersion: string;
  activationCode: string;
  activationName: string;
  category: string;
  status: "open" | "closed";
  eventUtc: string;
  activatedUtc: string;
  lastCheckedAt: string;
  sourceUrl: string;
  situationUrl: string;
  productsUrl: string;
  centroidWkt: string;
  extentWkt: string;
  imagery: {
    comparisonState: "scheduled" | "partial" | "ready";
    before: ColombiaImageryLayer | null;
    after: ColombiaImageryLayer | null;
    reference: ColombiaReferenceLayer;
  };
  aois: ColombiaMappingAoi[];
};

export type ColombiaMapMode = "map" | "reference" | "before" | "after";

export type ColombiaIncidentSource = {
  id: string;
  label: BilingualLabel;
  url: string;
  authority: "official-colombia" | "external-context" | string;
  role: string;
  publishedAt?: string;
  lastCheckedAt: string;
};

export type ColombiaIncident = {
  schemaVersion: string;
  incidentId: string;
  slug: string;
  status: string;
  statusLabel: BilingualLabel;
  activatedAt: string;
  lastVerifiedAt: string;
  verificationScope: BilingualLabel;
  event: {
    title: BilingualLabel;
    originLocal: string;
    originUtc: string;
    magnitude: number;
    latitude: number;
    longitude: number;
    depthKm: number;
    depthContext: {
      officialAlternativeKm: number;
      note: BilingualLabel;
    };
    reference: BilingualLabel;
    sourceEventId: string;
    usgsEventId: string;
  };
  tsunami: {
    status: "no-threat" | string;
    actionsRequired: boolean;
    issuedAt: string;
    summary: BilingualLabel;
    sourceId: string;
  };
  publicDamageLayer: {
    status: string;
    summary: BilingualLabel;
  };
  sourcePolicy: BilingualLabel;
  sources: ColombiaIncidentSource[];
  updatePolicy: BilingualLabel;
};
