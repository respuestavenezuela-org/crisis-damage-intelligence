export type EvidenceLanguage = "es" | "en";

export type EvidenceImage = {
  role: "pre_comparator" | "post_detection";
  sceneId: string;
  acquisitionUtc: string;
  sensor?: string;
  sourceFamily?: string;
  license?: string;
  provenanceStatus?: string;
  nativeImage: string;
  nativeLocalFallback?: string | null;
  nativeSha256: string;
  enhancedImage?: string | null;
  enhancedLocalFallback?: string | null;
  enhancementStatus?: string;
};

export type EvidencePair = {
  pairId: string;
  rank: number;
  rankScore: number;
  cellId: string;
  consensus: string;
  assetCategories: string[];
  targetDetection?: {
    class?: string;
    confidence?: number;
    xyxyn?: number[];
  };
  targetAcquisitionUtc?: string;
  targetWithinFirst72Hours?: boolean;
  images: EvidenceImage[];
  policy?: string;
};

export type EvidenceObservation = {
  cellId: string;
  longitude: number;
  latitude: number;
  cellBoundsWgs84?: number[][];
  coveredByAois: string[];
  stackStatus: "before_after" | "post_event_only";
  firstVisibleAcquisitionUtc?: string | null;
  hoursAfterEvent?: number | null;
  timeWindow: string;
  evidenceTier: string;
  consensus: string;
  priorityScore: number;
  assetCategories: string[];
  detector?: {
    sameAcquisitionCounts?: Record<string, number>;
    positiveMaxCountDeltas?: Record<string, number>;
    supportStatus?: string;
    warning?: string;
  };
  cropPairIds: string[];
  publicationStatus: string;
  arrivalInterpretation?: string;
};

export type EvidenceCellDetail = {
  version: number;
  updatedAt: string;
  publicationStatus: string;
  observation: EvidenceObservation;
  evidencePairs: EvidencePair[];
  pairCount: number;
  policy: {
    nativePixels: string;
    arrival: string;
    absence: string;
  };
};

export type EvidenceSummary = {
  updatedAt: string;
  status: string;
  scope: Record<EvidenceLanguage, string>;
  coverage: {
    gridCells: number;
    eligibleImageryStacks: number;
    pairedVlmCoverage: number;
    postEventOnlyCells: number;
    candidateCells: number;
    withinFirst72Hours: number;
    waldo30Cells: number;
    cropPairs: number;
    nativeCropImages: number;
    enhancedDisplayImages: number;
  };
  evidenceTierCounts: Record<string, number>;
  timeWindowCounts: Record<string, number>;
  assetCategoryCounts: Record<string, number>;
  timelineEvents: Array<{
    acquisitionUtc: string;
    hoursAfterEvent: number;
    timeWindow: string;
    candidateCells: number;
    bothModelsPositive: number;
    detectorSupported: number;
  }>;
  documentaryEvidence: {
    conflictsAndBounds: Array<{
      topic: string;
      topicEs?: string;
      finding: string;
      findingEs?: string;
      interpretation: string;
      interpretationEs?: string;
    }>;
    sources: Array<{
      id: string;
      publisher: string;
      sourceType: string;
      publishedAt: string;
      url: string;
      places: string[];
      claims: string[];
      claimsEs?: string[];
      timePrecision: string;
      limitations: string;
    }>;
  };
  downloads: {
    candidateGeoJson: string;
    candidateJsonl: string;
    cropManifest: string;
  };
  method: {
    vlmProviders: string[];
    detector: string;
    enhancement: string;
    arrivalRule: string;
    absenceRule: string;
  };
  guardrails: string[];
};

export type CuratedObservation = {
  id: string;
  chipId: string;
  status: "likely-response-related" | "unresolved";
  confidence: string;
  category: "heavy-machinery" | "large-vehicles" | "site-use";
  location: {
    label: string;
    latitude: number;
    longitude: number;
  };
  title: Record<EvidenceLanguage, string>;
  finding: Record<EvidenceLanguage, string>;
  nativeImage: string;
  nativeSha256: string;
  mapUrl: string;
};

export type CuratedEvidence = {
  observations: CuratedObservation[];
};
