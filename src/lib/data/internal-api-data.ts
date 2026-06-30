import { readFile } from "node:fs/promises";
import path from "node:path";
import { z } from "zod";
import {
  AoiRecordSchema,
  CatalogSchema,
  DamageFeatureCollectionSchema,
  PriorityQuerySchema,
  SearchQuerySchema,
  VlmRecordSchema,
  type AoiCatalog,
  type AoiRecord,
  type AoiStatus,
  type DamageFeature,
  type DamageFeatureCollection,
  type PriorityQuery,
  type SearchQuery,
  type SourceClass,
  type VlmRecord,
} from "@/lib/api/internal-contracts";
import { InternalApiHttpError, zodDetails } from "@/lib/api/internal-response";

const CATALOG_PATH = path.join(process.cwd(), "public", "data", "catalog.json");
const PUBLIC_AOI_ROOT = path.join(process.cwd(), "public", "data", "aoi");

let catalogPromise: Promise<AoiCatalog> | undefined;
const featureCollectionPromises = new Map<string, Promise<DamageFeatureCollection>>();
const vlmRecordPromises = new Map<string, Promise<VlmRecord[]>>();

function n(value: unknown) {
  return Number(value ?? 0) || 0;
}

function parseWithSchema<TSchema extends z.ZodType>(
  schema: TSchema,
  value: unknown,
  label: string,
): z.infer<TSchema> {
  const parsed = schema.safeParse(value);
  if (!parsed.success) {
    throw new InternalApiHttpError(500, "internal_data_invalid", `Static data failed validation at ${label}.`, {
      label,
      issues: zodDetails(parsed.error.issues),
    });
  }
  return parsed.data;
}

async function readJsonFile(filePath: string, label: string) {
  try {
    return JSON.parse(await readFile(filePath, "utf8")) as unknown;
  } catch (error) {
    throw new InternalApiHttpError(500, "internal_data_unavailable", `Unable to read ${label}.`, {
      label,
      message: error instanceof Error ? error.message : String(error),
    });
  }
}

function publicAoiDataPath(publicPath: string, label: string) {
  if (/^[a-z][a-z0-9+.-]*:\/\//i.test(publicPath)) {
    throw new InternalApiHttpError(500, "internal_data_invalid", `${label} must be a local public data path.`, {
      label,
      value: publicPath,
    });
  }
  if (!publicPath.startsWith("/data/aoi/") || publicPath.includes("\0")) {
    throw new InternalApiHttpError(500, "internal_data_invalid", `${label} is not a valid AOI public data path.`, {
      label,
      value: publicPath,
    });
  }

  const filePath = path.resolve(PUBLIC_AOI_ROOT, publicPath.slice("/data/aoi/".length));
  if (!filePath.startsWith(`${PUBLIC_AOI_ROOT}${path.sep}`)) {
    throw new InternalApiHttpError(500, "internal_data_invalid", `${label} escapes the public AOI data root.`, {
      label,
      value: publicPath,
    });
  }
  return filePath;
}

async function readCatalogFromDisk() {
  const raw = await readJsonFile(CATALOG_PATH, "public/data/catalog.json");
  return parseWithSchema(CatalogSchema, raw, "public/data/catalog.json");
}

export async function readCatalog() {
  catalogPromise ??= readCatalogFromDisk().catch((error) => {
    catalogPromise = undefined;
    throw error;
  });
  return catalogPromise;
}

export async function readAoi(id: string) {
  const catalog = await readCatalog();
  const aoi = catalog.aois.find((candidate) => candidate.id === id);
  if (!aoi) {
    throw new InternalApiHttpError(404, "aoi_not_found", `AOI ${id} was not found.`);
  }
  return parseWithSchema(AoiRecordSchema, aoi, `catalog.aois.${id}`);
}

async function readFeatureCollectionFromDisk(aoi: AoiRecord) {
  const filePath = publicAoiDataPath(aoi.layers.damage, `${aoi.id}.layers.damage`);
  const raw = await readJsonFile(filePath, `${aoi.id} damage GeoJSON`);
  return parseWithSchema(DamageFeatureCollectionSchema, raw, `${aoi.id}.damage.geojson`);
}

export async function readFeatureCollection(aoi: AoiRecord) {
  const key = aoi.id;
  let promise = featureCollectionPromises.get(key);
  if (!promise) {
    promise = readFeatureCollectionFromDisk(aoi).catch((error) => {
      featureCollectionPromises.delete(key);
      throw error;
    });
    featureCollectionPromises.set(key, promise);
  }
  return promise;
}

async function readVlmRecordsFromDisk(aoi: AoiRecord) {
  if (!aoi.layers.vlm) return [];

  const filePath = publicAoiDataPath(aoi.layers.vlm, `${aoi.id}.layers.vlm`);
  let text: string;
  try {
    text = await readFile(filePath, "utf8");
  } catch (error) {
    throw new InternalApiHttpError(500, "internal_data_unavailable", `Unable to read VLM data for ${aoi.id}.`, {
      aoiId: aoi.id,
      message: error instanceof Error ? error.message : String(error),
    });
  }

  return text
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line, index) => {
      let value: unknown;
      try {
        value = JSON.parse(line);
      } catch (error) {
        throw new InternalApiHttpError(500, "internal_data_invalid", `Invalid VLM JSONL row for ${aoi.id}.`, {
          aoiId: aoi.id,
          line: index + 1,
          message: error instanceof Error ? error.message : String(error),
        });
      }
      return parseWithSchema(VlmRecordSchema, value, `${aoi.id}.vlm.${index + 1}`);
    });
}

export async function readVlmRecords(aoi: AoiRecord) {
  const key = aoi.id;
  let promise = vlmRecordPromises.get(key);
  if (!promise) {
    promise = readVlmRecordsFromDisk(aoi).catch((error) => {
      vlmRecordPromises.delete(key);
      throw error;
    });
    vlmRecordPromises.set(key, promise);
  }
  return promise;
}

export function sourceClassForStatus(status: AoiStatus): SourceClass {
  if (status === "official-vector") return "official_ems_vector";
  if (status === "official-monitor-points") return "official_ems_monitor_points";
  if (status === "external-prediction") return "external_prediction_triage";
  if (status === "imagery-only" || status === "no-official-product" || status === "external-gap") {
    return "imagery_only_context";
  }
  if (status === "test-fixture") return "test_fixture";
  return "other";
}

function sourceRoleForAoi(aoi: AoiRecord) {
  const sourceClass = sourceClassForStatus(aoi.status);
  return {
    sourceClass,
    officialSourceOfRecord: sourceClass === "official_ems_vector",
    officialMonitorLayer: sourceClass === "official_ems_monitor_points",
    triageOnly: sourceClass === "external_prediction_triage",
    imageryOnlyContext: sourceClass === "imagery_only_context",
  };
}

function separatedMetrics(aoi: AoiRecord) {
  const role = sourceRoleForAoi(aoi);
  const vlmBeforeAfterReviewed = n(aoi.metrics.vlmBeforeAfterReviewed);
  const vlmPostEventReviewed = n(aoi.metrics.vlmPostEventReviewed);
  const hasVlm = Boolean(vlmBeforeAfterReviewed || vlmPostEventReviewed || n(aoi.metrics.vlmReviewed));

  return {
    officialEmsVector: role.sourceClass === "official_ems_vector"
      ? {
        features: n(aoi.metrics.features),
        destroyed: n(aoi.metrics.destroyed),
        damagedConfirmed: n(aoi.metrics.damagedConfirmed),
        possibleDamage: n(aoi.metrics.possibleDamage),
      }
      : null,
    officialEmsMonitorPoints: role.sourceClass === "official_ems_monitor_points"
      ? {
        features: n(aoi.metrics.features),
        destroyed: n(aoi.metrics.destroyed),
        damagedConfirmed: n(aoi.metrics.damagedConfirmed),
        possibleDamage: n(aoi.metrics.possibleDamage),
      }
      : null,
    externalPredictionTriage: role.sourceClass === "external_prediction_triage"
      ? {
        candidates: n(aoi.metrics.candidates ?? aoi.metrics.features),
        features: n(aoi.metrics.features),
      }
      : null,
    imageryOnlyContext: role.sourceClass === "imagery_only_context"
      ? {
        features: n(aoi.metrics.features),
      }
      : null,
    vlmTriage: hasVlm
      ? {
        reviewedLegacy: n(aoi.metrics.vlmReviewed),
        beforeAfterReviewed: vlmBeforeAfterReviewed,
        beforeAfterSkippedNoBefore: n(aoi.metrics.vlmBeforeAfterSkippedNoBefore),
        beforeAfterUncertain: n(aoi.metrics.vlmBeforeAfterUncertain),
        beforeAfterLikelyDestroyed: n(aoi.metrics.vlmBeforeAfterLikelyDestroyed),
        beforeAfterPossibleMajor: n(aoi.metrics.vlmBeforeAfterPossibleMajor),
        beforeAfterActionable: n(aoi.metrics.vlmBeforeAfterActionable),
        beforeAfterUrgentReview: n(aoi.metrics.vlmBeforeAfterUrgentReview),
        postEventReviewed: vlmPostEventReviewed,
        postEventUncertain: n(aoi.metrics.vlmPostEventUncertain),
        postEventLikelyDestroyed: n(aoi.metrics.vlmPostEventLikelyDestroyed),
        postEventPossibleMajor: n(aoi.metrics.vlmPostEventPossibleMajor),
        postEventUrgentReview: n(aoi.metrics.vlmPostEventUrgentReview),
        triageOnly: true,
      }
      : null,
  };
}

export function toAoiContract(aoi: AoiRecord) {
  return {
    id: aoi.id,
    country: aoi.country,
    event: aoi.event,
    name: aoi.name,
    status: aoi.status,
    source: aoi.source,
    sourceRole: sourceRoleForAoi(aoi),
    bounds: aoi.bounds,
    center: aoi.center,
    downloads: aoi.downloads,
    layers: aoi.layers,
    imagery: aoi.imagery ?? null,
    metrics: separatedMetrics(aoi),
    rawMetricsFromCatalog: aoi.metrics,
  };
}

export function toAoiListItem(aoi: AoiRecord) {
  return {
    id: aoi.id,
    name: aoi.name,
    status: aoi.status,
    sourceRole: sourceRoleForAoi(aoi),
    bounds: aoi.bounds,
    center: aoi.center,
    downloadFormats: Object.keys(aoi.downloads).sort(),
    layerKinds: Object.keys(aoi.layers).sort(),
    metrics: separatedMetrics(aoi),
    rawMetricsFromCatalog: aoi.metrics,
  };
}

function normalizeFeatureForAoi(feature: DamageFeature, aoi: AoiRecord): DamageFeature {
  const sourceFeatureId = String(feature.properties.id);
  return {
    ...feature,
    properties: {
      ...feature.properties,
      id: `${aoi.id}__${sourceFeatureId}`,
      source_feature_id: sourceFeatureId,
      aoi_id: aoi.id,
      aoi_label_en: aoi.name.en,
      aoi_label_es: aoi.name.es,
      source_class: sourceClassForStatus(aoi.status),
      official_source_of_record: aoi.status === "official-vector",
      official_monitor_layer: aoi.status === "official-monitor-points",
      triage_only: aoi.status === "external-prediction",
    },
  };
}

function stringValue(value: unknown) {
  return typeof value === "string" ? value : value == null ? "" : String(value);
}

function numberOrNull(value: unknown) {
  if (value == null || value === "") return null;
  const next = Number(value);
  return Number.isFinite(next) ? next : null;
}

function officialSeverityScore(cls: string) {
  const normalized = cls.toLowerCase();
  if (normalized.includes("destroy")) return 12_000;
  if (normalized.includes("possibly")) return 8_000;
  if (normalized.includes("damage") || normalized.includes("major")) return 11_000;
  if (normalized.includes("minor")) return 7_000;
  return 0;
}

function vlmSeverityScore(vlm?: VlmRecord) {
  const cls = stringValue(vlm?.vlm?.damage_class).toLowerCase();
  const reviewType = stringValue(vlm?.vlm?.review_type ?? vlm?.review_type);
  const beforeAfterBonus = reviewType.includes("before") || reviewType.includes("comparison") ? 300 : 0;
  if (cls.includes("likely_destroyed") || cls.includes("likely destroyed")) return 5_200 + beforeAfterBonus;
  if (cls.includes("possible_major") || cls.includes("possible major")) return 4_700 + beforeAfterBonus;
  if (cls.includes("minor")) return 3_700 + beforeAfterBonus;
  return vlm ? 3_000 + beforeAfterBonus : 0;
}

function priorityFeatureScore(feature: DamageFeature, vlm: VlmRecord | undefined, status: AoiStatus) {
  const properties = feature.properties;
  const cls = stringValue(properties.damage_class ?? properties.damage_gra ?? properties.confirmed_damage_class);
  const numeric = n(properties.damage_score ?? properties.damage_percent ?? properties.confirmed_damage_percent);
  if (status === "official-vector") return officialSeverityScore(cls) + numeric + Math.min(vlmSeverityScore(vlm) / 100, 80);
  if (status === "official-monitor-points") return Math.max(officialSeverityScore(cls) - 2_000, 6_000) + numeric;
  if (status === "external-prediction") return 3_000 + numeric;
  return vlmSeverityScore(vlm) + numeric;
}

function vlmEvidenceMode(vlm: VlmRecord) {
  const reviewType = stringValue(vlm.vlm?.review_type ?? vlm.review_type).toLowerCase();
  if (reviewType === "post_event_only") return "post_event_only";
  if (
    reviewType.includes("pre_event")
    || reviewType.includes("before_after")
    || reviewType.includes("comparison")
  ) {
    return "before_after";
  }
  return "triage_evidence";
}

function priorityItem(feature: DamageFeature, vlm: VlmRecord | undefined, aoi: AoiRecord, rank: number, score: number) {
  const properties = feature.properties;
  const sourceFeatureId = stringValue(properties.source_feature_id ?? properties.id);
  const damageClass = stringValue(properties.damage_class ?? properties.damage_gra ?? properties.confirmed_damage_class);
  const evidenceMode = vlm ? vlmEvidenceMode(vlm) : null;
  const centroidLat = numberOrNull(properties.centroid_lat);
  const centroidLon = numberOrNull(properties.centroid_lon);
  const googleMapsUrl = stringValue(properties.google_maps_url ?? vlm?.google_maps_url)
    || (centroidLat != null && centroidLon != null ? `https://www.google.com/maps/search/?api=1&query=${centroidLat},${centroidLon}` : null);

  return {
    id: `${aoi.id}__${sourceFeatureId}`,
    aoi_id: aoi.id,
    source_feature_id: sourceFeatureId,
    google_maps_url: googleMapsUrl,
    rank,
    score: Math.round(score * 100) / 100,
    featureId: `${aoi.id}__${sourceFeatureId}`,
    sourceFeatureId,
    aoiId: aoi.id,
    aoiStatus: aoi.status,
    sourceRole: sourceRoleForAoi(aoi),
    official: {
      sourceOfRecord: aoi.status === "official-vector",
      monitorLayer: aoi.status === "official-monitor-points",
      damageClass,
      damagePercent: numberOrNull(properties.damage_percent ?? properties.confirmed_damage_percent),
    },
    triage: {
      externalPrediction: aoi.status === "external-prediction"
        ? {
          triageOnly: true,
          damageClass,
          damagePercent: numberOrNull(properties.damage_percent),
        }
        : null,
      vlm: vlm
        ? {
          triageOnly: true,
          evidenceMode,
          beforeAfterComparison: evidenceMode === "before_after",
          postEventOnly: evidenceMode === "post_event_only",
          reviewType: stringValue(vlm.vlm?.review_type ?? vlm.review_type) || null,
          damageClass: vlm.vlm?.damage_class ?? null,
          damagePercent: numberOrNull(vlm.vlm?.damage_percent),
          confidence: vlm.vlm?.confidence ?? null,
          actionPriority: vlm.vlm?.action_priority ?? null,
          model: vlm.vlm?.vlm_model ?? null,
          chips: {
            beforeEvent: vlm.before_event_chip ?? null,
            postEvent: vlm.post_event_chip ?? null,
            compare: vlm.compare_chip ?? null,
            triplet: vlm.triplet_chip ?? null,
          },
          evidenceText: vlm.vlm?.change_evidence ?? vlm.vlm?.evidence ?? vlm.vlm?.visible_evidence ?? null,
          uncertaintyReason: vlm.vlm?.uncertainty_reason ?? null,
        }
        : null,
    },
    location: {
      centroidLat,
      centroidLon,
      googleMapsUrl,
    },
    feature,
  };
}

export async function catalogPayload() {
  const catalog = await readCatalog();
  return {
    sourcePath: "/data/catalog.json",
    updatedAt: catalog.updatedAt,
    platform: catalog.platform,
    aoiCount: catalog.aois.length,
    watchlist: catalog.watchlist,
    aois: catalog.aois.map(toAoiContract),
  };
}

export async function aoisPayload() {
  const catalog = await readCatalog();
  return {
    sourcePath: "/data/catalog.json",
    updatedAt: catalog.updatedAt,
    count: catalog.aois.length,
    aois: catalog.aois.map(toAoiListItem),
  };
}

export async function aoiPayload(id: string) {
  const aoi = await readAoi(id);
  return {
    sourcePath: "/data/catalog.json",
    ...toAoiContract(aoi),
  };
}

export async function featuresPayload(id: string) {
  const aoi = await readAoi(id);
  const collection = await readFeatureCollection(aoi);
  const features = collection.features.map((feature) => normalizeFeatureForAoi(feature, aoi));

  return {
    aoi: toAoiListItem(aoi),
    featureCount: features.length,
    sourcePath: aoi.layers.damage,
    features,
    featureCollection: {
      ...collection,
      features,
    },
  };
}

export async function priorityPayload(id: string, query: PriorityQuery) {
  const aoi = await readAoi(id);
  const collection = await readFeatureCollection(aoi);
  const features = collection.features.map((feature) => normalizeFeatureForAoi(feature, aoi));
  const vlmById = new Map((await readVlmRecords(aoi)).map((record) => [record.id, record]));
  const scored = features
    .map((feature) => {
      const sourceFeatureId = stringValue(feature.properties.source_feature_id ?? feature.properties.id);
      const vlm = vlmById.get(sourceFeatureId);
      return {
        feature,
        vlm,
        score: priorityFeatureScore(feature, vlm, aoi.status),
      };
    })
    .sort((left, right) => (
      right.score - left.score
      || stringValue(left.feature.properties.source_feature_id).localeCompare(stringValue(right.feature.properties.source_feature_id))
    ))
    .slice(0, query.limit);

  return {
    aoi: toAoiListItem(aoi),
    query: {
      limit: query.limit,
      returned: scored.length,
      candidateFeatureCount: features.length,
      vlmRecordsRead: vlmById.size,
    },
    sourcePaths: {
      damage: aoi.layers.damage,
      vlm: aoi.layers.vlm ?? null,
    },
    items: scored.map((item, index) => priorityItem(item.feature, item.vlm, aoi, index + 1, item.score)),
  };
}

function normalizeSearchText(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function matchScore(query: string, fields: Record<string, string>) {
  const matchedFields: string[] = [];
  let score = 0;
  for (const [field, value] of Object.entries(fields)) {
    const normalized = normalizeSearchText(value);
    if (!normalized) continue;
    if (normalized === query) {
      matchedFields.push(field);
      score += 100;
    } else if (normalized.includes(query)) {
      matchedFields.push(field);
      score += field === "id" ? 70 : 35;
    }
  }
  return { score, matchedFields };
}

export async function searchPayload(query: SearchQuery) {
  const catalog = await readCatalog();
  const normalizedQuery = normalizeSearchText(query.q);
  const aoiResults = catalog.aois.flatMap((aoi) => {
      const match = matchScore(normalizedQuery, {
        id: aoi.id,
        nameEn: aoi.name.en,
        nameEs: aoi.name.es,
        status: aoi.status,
        source: aoi.source,
      });
      return match.score > 0
        ? [{
          id: aoi.id,
          type: "aoi" as const,
          label: aoi.name.es || aoi.name.en || aoi.id,
          score: match.score,
          matchedFields: match.matchedFields,
          item: toAoiListItem(aoi),
        }]
        : [];
    });

  const watchlistResults = catalog.watchlist.flatMap((item) => {
      const match = matchScore(normalizedQuery, {
        id: item.id,
        nameEn: item.name.en,
        nameEs: item.name.es,
        status: item.status,
        priority: item.priority,
      });
      return match.score > 0
        ? [{
          id: item.id,
          type: "watchlist" as const,
          label: item.name.es || item.name.en || item.id,
          score: match.score,
          matchedFields: match.matchedFields,
          item,
        }]
        : [];
    });

  const featureResults = normalizedQuery.length >= 4 && /(?:^|[_-])[a-z]{2,5}[_-]?\d+|\d{3,}/i.test(query.q)
    ? await searchFeatureIds(catalog.aois, normalizedQuery, Math.max(0, query.limit - aoiResults.length - watchlistResults.length))
    : [];

  const results = [...aoiResults, ...watchlistResults, ...featureResults]
    .sort((left, right) => right.score - left.score)
    .slice(0, query.limit);

  return {
    query: {
      q: query.q,
      normalized: normalizedQuery,
      limit: query.limit,
      resultCount: results.length,
      searched: ["catalog.aois", "catalog.watchlist"],
      featureSearch: {
        performed: featureResults.length > 0,
        reason: featureResults.length > 0
          ? "Feature id lookup only; broad queries stay metadata-only to avoid unnecessary AOI GeoJSON reads."
          : "Search stayed metadata-only because the query did not look like a feature id.",
      },
    },
    results,
  };
}

async function searchFeatureIds(aois: AoiRecord[], normalizedQuery: string, limit: number) {
  if (limit <= 0) return [];
  const results: Array<{
    id: string;
    type: "feature";
    label: string;
    score: number;
    matchedFields: string[];
    item: {
      id: string;
      sourceFeatureId: string;
      aoi: ReturnType<typeof toAoiListItem>;
      damageClass: string;
      triageOnly: boolean;
    };
  }> = [];

  for (const aoi of aois) {
    if (results.length >= limit) break;
    const collection = await readFeatureCollection(aoi);
    for (const feature of collection.features) {
      const sourceFeatureId = stringValue(feature.properties.id);
      const normalizedSourceId = normalizeSearchText(sourceFeatureId);
      if (!normalizedSourceId.includes(normalizedQuery)) continue;
      const damageClass = stringValue(feature.properties.damage_class ?? feature.properties.damage_gra ?? feature.properties.confirmed_damage_class);
      results.push({
        id: sourceFeatureId,
        type: "feature",
        label: sourceFeatureId,
        score: normalizedSourceId === normalizedQuery ? 95 : 65,
        matchedFields: ["sourceFeatureId"],
        item: {
          id: `${aoi.id}__${sourceFeatureId}`,
          sourceFeatureId,
          aoi: toAoiListItem(aoi),
          damageClass,
          triageOnly: aoi.status === "external-prediction",
        },
      });
      if (results.length >= limit) break;
    }
  }

  return results;
}

function sumByStatus(aois: AoiRecord[], status: AoiStatus) {
  const records = aois.filter((aoi) => aoi.status === status);
  return {
    aoiCount: records.length,
    features: records.reduce((sum, aoi) => sum + n(aoi.metrics.features), 0),
    destroyed: records.reduce((sum, aoi) => sum + n(aoi.metrics.destroyed), 0),
    damagedConfirmed: records.reduce((sum, aoi) => sum + n(aoi.metrics.damagedConfirmed), 0),
    possibleDamage: records.reduce((sum, aoi) => sum + n(aoi.metrics.possibleDamage), 0),
  };
}

export async function summaryPayload() {
  const catalog = await readCatalog();
  const statusCounts = catalog.aois.reduce<Record<string, number>>((counts, aoi) => {
    counts[aoi.status] = (counts[aoi.status] ?? 0) + 1;
    return counts;
  }, {});

  return {
    sourcePath: "/data/catalog.json",
    updatedAt: catalog.updatedAt,
    platform: catalog.platform,
    aoiCount: catalog.aois.length,
    watchlistCount: catalog.watchlist.length,
    statusCounts,
    totals: {
      officialEmsVectors: sumByStatus(catalog.aois, "official-vector"),
      officialEmsMonitorPoints: sumByStatus(catalog.aois, "official-monitor-points"),
      externalPredictionTriage: {
        aoiCount: catalog.aois.filter((aoi) => aoi.status === "external-prediction").length,
        candidates: catalog.aois
          .filter((aoi) => aoi.status === "external-prediction")
          .reduce((sum, aoi) => sum + n(aoi.metrics.candidates ?? aoi.metrics.features), 0),
        features: catalog.aois
          .filter((aoi) => aoi.status === "external-prediction")
          .reduce((sum, aoi) => sum + n(aoi.metrics.features), 0),
      },
      imageryOnlyContext: {
        aoiCount: catalog.aois.filter((aoi) => sourceClassForStatus(aoi.status) === "imagery_only_context").length,
      },
      vlmTriage: {
        beforeAfterReviewed: catalog.aois.reduce((sum, aoi) => sum + n(aoi.metrics.vlmBeforeAfterReviewed), 0),
        beforeAfterActionable: catalog.aois.reduce((sum, aoi) => sum + n(aoi.metrics.vlmBeforeAfterActionable), 0),
        beforeAfterUrgentReview: catalog.aois.reduce((sum, aoi) => sum + n(aoi.metrics.vlmBeforeAfterUrgentReview), 0),
        postEventReviewed: catalog.aois.reduce((sum, aoi) => sum + n(aoi.metrics.vlmPostEventReviewed), 0),
        postEventUrgentReview: catalog.aois.reduce((sum, aoi) => sum + n(aoi.metrics.vlmPostEventUrgentReview), 0),
        triageOnly: true,
      },
    },
  };
}

export function parseSearchParams(searchParams: URLSearchParams) {
  const parsed = SearchQuerySchema.safeParse({
    q: searchParams.get("q") ?? "",
    limit: searchParams.get("limit") ?? undefined,
  });
  if (!parsed.success) {
    throw new InternalApiHttpError(400, "invalid_query", "Invalid search query.", {
      issues: zodDetails(parsed.error.issues),
    });
  }
  return parsed.data;
}

export function parsePriorityParams(searchParams: URLSearchParams) {
  const parsed = PriorityQuerySchema.safeParse({
    limit: searchParams.get("limit") ?? undefined,
  });
  if (!parsed.success) {
    throw new InternalApiHttpError(400, "invalid_query", "Invalid priority query.", {
      issues: zodDetails(parsed.error.issues),
    });
  }
  return parsed.data;
}

export function parseAoiIdParam(searchParams: URLSearchParams) {
  const id = searchParams.get("aoi_id")?.trim();
  if (!id) {
    throw new InternalApiHttpError(400, "invalid_query", "Missing required aoi_id query parameter.");
  }
  return id;
}
