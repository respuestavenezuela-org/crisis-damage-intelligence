export type Language = "en" | "es";

export type AoiRecord = {
  id: string;
  country: string;
  event: string;
  name: Record<Language, string>;
  status: string;
  source: string;
  bounds: [[number, number], [number, number]];
  center: [number, number];
  downloads: Record<string, string>;
  layers: {
    damage: string;
    beforeImage?: string;
    afterImage?: string;
    beforeTiles?: string;
    afterTiles?: string;
    vlm?: string;
  };
  imagery?: {
    before: null | {
      url: string;
      sensor?: string;
      acquisitionUtc?: string;
      bytes?: number;
      sha256?: string;
      r2Key?: string;
      source?: string;
      coverage?: string;
      license?: string;
      tilePyramid?: {
        urlTemplate: string;
        format?: string;
        minZoom?: number;
        maxZoom?: number;
        tileCount?: number;
        bytesApprox?: number;
        quality?: number;
      };
      sourceScenes?: Array<{
        id: string;
        sensor?: string;
        acquisitionUtc?: string;
        cloudCover?: number;
        url?: string;
      }>;
    };
    after: null | {
      url: string;
      sensor?: string;
      acquisitionUtc?: string;
      bytes?: number;
      sha256?: string;
      r2Key?: string;
      tilePyramid?: {
        urlTemplate: string;
        format?: string;
        minZoom?: number;
        maxZoom?: number;
        tileCount?: number;
        bytesApprox?: number;
        quality?: number;
      };
    };
    approximateReference?: {
      label: string;
      urlTemplate: string;
      source?: string;
      intendedUse?: string;
      limitations?: string;
    };
    note?: string;
  };
  metrics: Record<string, number>;
};

export type AoiCatalog = {
  updatedAt: string;
  platform: string;
  aois: AoiRecord[];
  watchlist: Array<{
    id: string;
    name: Record<Language, string>;
    status: string;
    expectedUtc: string;
    priority: string;
  }>;
};

export type DamageFeature = {
  type: "Feature";
  geometry: GeoJSON.Geometry;
  properties: Record<string, string | number | boolean | undefined> & { id: string };
};

export type VlmRecord = {
  id: string;
  triplet_chip?: string;
  compare_chip?: string;
  before_event_chip?: string;
  post_event_chip?: string;
  review_type?: string;
  official_ems_damage_gra?: string;
  official_ems_damage_percent?: number;
  truth_damage_class?: string;
  vlm?: {
    damage_class?: string;
    damage_percent?: number;
    confidence?: number | string;
    change_evidence?: string;
    before_observation?: string;
    after_observation?: string;
    image_alignment?: string;
    evidence?: string;
    visible_evidence?: string;
    image_quality?: string;
    action_priority?: string;
    review_type?: string;
    uncertainty_reason?: string;
  };
};
