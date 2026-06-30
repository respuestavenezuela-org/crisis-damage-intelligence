import { z } from "zod";

export const INTERNAL_API_VERSION = "internal.v1";

export const INTERNAL_API_SOURCE_LABELS = {
  officialEmsVector: {
    statuses: ["official-vector"],
    role: "Copernicus EMS builtUpA vector products are the official damage source of record where present.",
  },
  officialEmsMonitorPoints: {
    statuses: ["official-monitor-points"],
    role: "Copernicus EMS MONIT01 point layers are official monitoring leads and stay separate from builtUpA vector counts.",
  },
  imageryOnly: {
    statuses: ["imagery-only", "no-official-product", "external-gap"],
    role: "Imagery-only records provide context and do not publish official damage counts.",
  },
  externalPredictionTriage: {
    statuses: ["external-prediction"],
    role: "External prediction layers are search and triage leads only, not official EMS damage labels.",
  },
  vlmTriage: {
    statuses: ["vlm"],
    role: "VLM outputs are asynchronous evidence aids only and are never public runtime model calls.",
  },
} as const;

export const INTERNAL_API_CAVEATS = [
  "Copernicus EMS official vectors remain the source of record for official damage labels.",
  "MONIT01 point layers stay separate from builtUpA polygon counts.",
  "External predictions, VLM outputs, OSM, and heuristics are triage or evidence only.",
  "Absence of a feature, VLM signal, or imagery coverage must not be treated as absence of damage.",
  "post_event_only VLM records must not be interpreted as before/after comparison evidence.",
] as const;

export const AoiStatusSchema = z.enum([
  "test-fixture",
  "official-vector",
  "official-monitor-points",
  "external-prediction",
  "imagery-only",
  "waiting",
  "in-production",
  "no-official-product",
  "external-gap",
]);

export const LocalizedNameSchema = z.object({
  en: z.string(),
  es: z.string(),
});

export const AoiRecordSchema = z
  .object({
    id: z.string().min(1),
    country: z.string().min(1),
    event: z.string().min(1),
    name: LocalizedNameSchema,
    status: AoiStatusSchema,
    source: z.string().min(1),
    bounds: z.tuple([
      z.tuple([z.number(), z.number()]),
      z.tuple([z.number(), z.number()]),
    ]),
    center: z.tuple([z.number(), z.number()]),
    downloads: z.record(z.string(), z.string()),
    layers: z
      .object({
        damage: z.string().min(1),
        beforeImage: z.string().optional(),
        afterImage: z.string().optional(),
        beforeTiles: z.string().optional(),
        afterTiles: z.string().optional(),
        vlm: z.string().optional(),
      })
      .catchall(z.string()),
    imagery: z.unknown().optional(),
    metrics: z.record(z.string(), z.number()),
  })
  .passthrough();

export const WatchlistItemSchema = z
  .object({
    id: z.string().min(1),
    name: LocalizedNameSchema,
    status: z.string().min(1),
    expectedUtc: z.string().min(1),
    priority: z.string().min(1),
  })
  .passthrough();

export const CatalogSchema = z
  .object({
    updatedAt: z.string().min(1),
    platform: z.string().min(1),
    aois: z.array(AoiRecordSchema),
    watchlist: z.array(WatchlistItemSchema),
  })
  .passthrough();

export const FeaturePropertiesSchema = z
  .object({
    id: z.union([z.string(), z.number()]),
  })
  .catchall(z.unknown());

export const GeoJsonGeometrySchema = z
  .object({
    type: z.string().min(1),
  })
  .passthrough()
  .nullable();

export const DamageFeatureSchema = z
  .object({
    type: z.literal("Feature"),
    geometry: GeoJsonGeometrySchema,
    properties: FeaturePropertiesSchema,
  })
  .passthrough();

export const DamageFeatureCollectionSchema = z
  .object({
    type: z.literal("FeatureCollection"),
    features: z.array(DamageFeatureSchema),
  })
  .passthrough();

export const VlmPayloadSchema = z
  .object({
    damage_class: z.string().optional(),
    damage_percent: z.union([z.number(), z.string(), z.null()]).optional(),
    confidence: z.union([z.number(), z.string(), z.null()]).optional(),
    change_evidence: z.string().optional(),
    before_observation: z.string().optional(),
    after_observation: z.string().optional(),
    evidence: z.string().optional(),
    visible_evidence: z.string().optional(),
    image_alignment: z.string().optional(),
    image_quality: z.string().optional(),
    action_priority: z.string().optional(),
    review_type: z.string().optional(),
    uncertainty_reason: z.string().optional(),
    vlm_model: z.string().optional(),
    before_source: z.string().optional(),
  })
  .catchall(z.unknown());

export const VlmRecordSchema = z
  .object({
    id: z.string().min(1),
    aoi_id: z.string().optional(),
    triplet_chip: z.string().optional(),
    compare_chip: z.string().optional(),
    before_event_chip: z.string().optional(),
    post_event_chip: z.string().optional(),
    review_type: z.string().optional(),
    official_ems_damage_gra: z.string().optional(),
    official_ems_damage_percent: z.number().optional(),
    truth_damage_class: z.string().optional(),
    google_maps_url: z.string().optional(),
    vlm: VlmPayloadSchema.optional(),
  })
  .catchall(z.unknown());

export const SearchQuerySchema = z.object({
  q: z.string().trim().min(2).max(120),
  limit: z.coerce.number().int().min(1).max(50).default(20),
});

export const PriorityQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(50).default(12),
});

export type AoiStatus = z.infer<typeof AoiStatusSchema>;
export type AoiRecord = z.infer<typeof AoiRecordSchema>;
export type AoiCatalog = z.infer<typeof CatalogSchema>;
export type DamageFeature = z.infer<typeof DamageFeatureSchema>;
export type DamageFeatureCollection = z.infer<typeof DamageFeatureCollectionSchema>;
export type VlmRecord = z.infer<typeof VlmRecordSchema>;
export type SearchQuery = z.infer<typeof SearchQuerySchema>;
export type PriorityQuery = z.infer<typeof PriorityQuerySchema>;

export type SourceClass =
  | "official_ems_vector"
  | "official_ems_monitor_points"
  | "external_prediction_triage"
  | "imagery_only_context"
  | "test_fixture"
  | "other";
