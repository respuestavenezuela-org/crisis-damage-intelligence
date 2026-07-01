"use client";

import { track as trackVercel } from "@vercel/analytics";

export type AnalyticsEventName =
  | "app_loaded"
  | "language_switched"
  | "aoi_selected"
  | "imagery_mode_changed"
  | "basemap_changed"
  | "damage_filter_changed"
  | "operational_signals_toggled"
  | "operational_signal_clicked"
  | "priority_item_clicked"
  | "google_maps_link_clicked"
  | "translator_open"
  | "translator_telegram"
  | "data_download_clicked"
  | "evidence_chip_clicked"
  | "map_ready"
  | "first_tile_loaded"
  | "first_interaction_seconds"
  | "catalog_load_failed"
  | "layer_load_failed"
  | "fallback_view_shown"
  | "filter_empty_result_seen"
  | "map_empty_clicked"
  | "mobile_panel_opened";

export type AnalyticsProperty = string | number | boolean | null | undefined;
export type AnalyticsProperties = Record<string, AnalyticsProperty>;

export type AnalyticsEvent = {
  name: AnalyticsEventName;
  properties: Record<string, Exclude<AnalyticsProperty, undefined>>;
};

const analyticsPropertyAllowlist = {
  app_loaded: ["language", "default_aoi_id", "aoi_count", "default_basemap", "default_mode", "public_static"],
  language_switched: ["from_language", "to_language", "aoi_id"],
  aoi_selected: ["aoi_id", "city_id", "aoi_status", "language"],
  imagery_mode_changed: ["aoi_id", "mode", "has_before_imagery", "has_after_imagery"],
  basemap_changed: ["aoi_id", "basemap"],
  damage_filter_changed: ["aoi_id", "filter"],
  operational_signals_toggled: ["aoi_id", "status", "signal_count", "language"],
  operational_signal_clicked: ["aoi_id", "rank", "signal_priority", "signal_id", "surface"],
  priority_item_clicked: ["aoi_id", "rank", "damage_class", "has_vlm", "vlm_review_type"],
  google_maps_link_clicked: ["aoi_id", "surface", "has_vlm"],
  translator_open: ["surface", "language"],
  translator_telegram: ["surface", "language"],
  data_download_clicked: ["aoi_id", "format", "surface"],
  evidence_chip_clicked: ["aoi_id", "chip_kind", "surface", "has_vlm"],
  map_ready: ["aoi_id", "feature_count", "mode", "basemap"],
  first_tile_loaded: ["aoi_id", "layer", "mode", "basemap"],
  first_interaction_seconds: ["seconds", "surface", "aoi_id", "language"],
  catalog_load_failed: ["surface", "status"],
  layer_load_failed: ["aoi_id", "layer", "surface", "status", "mode", "basemap"],
  fallback_view_shown: ["aoi_id", "surface", "status", "catalog_status", "damage_status", "vlm_status"],
  filter_empty_result_seen: ["aoi_id", "filter", "mode", "basemap", "feature_count", "status"],
  map_empty_clicked: ["aoi_id", "mode", "filter", "basemap"],
  mobile_panel_opened: ["aoi_id", "surface", "language", "mode", "filter", "basemap"],
} satisfies Record<AnalyticsEventName, readonly string[]>;

type SanitizedAnalyticsProperty = Exclude<AnalyticsProperty, undefined>;
type AnalyticsValueSanitizer = (value: AnalyticsProperty) => SanitizedAnalyticsProperty | undefined;

const sensitiveStringPatterns = [
  /https?:\/\//i,
  /\bwww\./i,
  /\/data\/(?:aoi|chips|tiles)\//i,
  /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i,
  /-?\d{1,2}\.\d{4,}\s*,\s*-?\d{1,3}\.\d{4,}/,
];

const coarseIdPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const safeTokenPattern = /^[a-z0-9][a-z0-9_-]{0,79}$/;
const safeLabelPattern = /^[a-zA-Z0-9][a-zA-Z0-9 _.:/-]{0,119}$/;

function sanitizeString(value: AnalyticsProperty, pattern: RegExp) {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  if (sensitiveStringPatterns.some((pattern) => pattern.test(trimmed))) return undefined;
  return pattern.test(trimmed) ? trimmed : undefined;
}

const asBoolean: AnalyticsValueSanitizer = (value) => (typeof value === "boolean" ? value : undefined);
const asCoarseId: AnalyticsValueSanitizer = (value) => sanitizeString(value, coarseIdPattern);
const asSafeToken: AnalyticsValueSanitizer = (value) => sanitizeString(value, safeTokenPattern);
const asSafeLabel: AnalyticsValueSanitizer = (value) => sanitizeString(value, safeLabelPattern);
const asNonNegativeInteger: AnalyticsValueSanitizer = (value) => (
  typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 1_000_000 ? value : undefined
);
const asPositiveRank: AnalyticsValueSanitizer = (value) => (
  typeof value === "number" && Number.isInteger(value) && value >= 1 && value <= 1_000 ? value : undefined
);
const asElapsedSeconds: AnalyticsValueSanitizer = (value) => (
  typeof value === "number" && Number.isInteger(value) && value >= 0 && value <= 86_400 ? value : undefined
);

function oneOf<T extends string>(allowed: readonly T[]): AnalyticsValueSanitizer {
  return (value) => (typeof value === "string" && allowed.includes(value.trim() as T) ? value.trim() : undefined);
}

const analyticsPropertySanitizers: Record<string, AnalyticsValueSanitizer> = {
  aoi_count: asNonNegativeInteger,
  aoi_id: asCoarseId,
  aoi_status: asSafeToken,
  basemap: oneOf(["map", "aerial"]),
  catalog_status: asSafeToken,
  chip_kind: asSafeToken,
  city_id: asCoarseId,
  damage_class: asSafeLabel,
  damage_status: asSafeToken,
  default_aoi_id: asCoarseId,
  default_basemap: oneOf(["map", "aerial"]),
  default_mode: oneOf(["before", "after"]),
  feature_count: asNonNegativeInteger,
  filter: oneOf(["all", "severe", "vlm"]),
  format: asSafeToken,
  from_language: oneOf(["es", "en"]),
  has_after_imagery: asBoolean,
  has_before_imagery: asBoolean,
  has_vlm: asBoolean,
  language: oneOf(["es", "en"]),
  layer: asSafeToken,
  mode: oneOf(["before", "after"]),
  public_static: asBoolean,
  rank: asPositiveRank,
  seconds: asElapsedSeconds,
  signal_count: asNonNegativeInteger,
  signal_id: asSafeToken,
  signal_priority: oneOf(["high", "medium", "low"]),
  status: asSafeToken,
  surface: asSafeToken,
  to_language: oneOf(["es", "en"]),
  vlm_review_type: asSafeToken,
  vlm_status: asSafeToken,
};

declare global {
  interface Window {
    crisisDamageAnalytics?: {
      track: (event: AnalyticsEvent) => void;
    };
    crisisDamageAnalyticsQueue?: AnalyticsEvent[];
  }
}

const provider = (process.env.NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER ?? "disabled").trim();
const openPanelClientId = (process.env.NEXT_PUBLIC_OPENPANEL_CLIENT_ID ?? "").trim();
const debug = process.env.NEXT_PUBLIC_ANALYTICS_DEBUG === "true";

function compactProperties(name: AnalyticsEventName, properties: AnalyticsProperties = {}) {
  const allowed = analyticsPropertyAllowlist[name];
  return Object.fromEntries(
    Object.entries(properties).flatMap(([key, value]) => {
      if (!allowed.includes(key)) return [];
      const sanitizer = analyticsPropertySanitizers[key];
      if (!sanitizer) return [];
      const sanitized = sanitizer(value);
      return sanitized === undefined ? [] : [[key, sanitized]];
    }),
  ) as AnalyticsEvent["properties"];
}

export function trackAnalytics(name: AnalyticsEventName, properties: AnalyticsProperties = {}) {
  if (typeof window === "undefined") return;

  const event: AnalyticsEvent = {
    name,
    properties: compactProperties(name, properties),
  };

  window.crisisDamageAnalyticsQueue = window.crisisDamageAnalyticsQueue ?? [];
  window.crisisDamageAnalyticsQueue.push(event);
  window.crisisDamageAnalytics?.track(event);
  window.dispatchEvent(new CustomEvent("crisis_damage_analytics", { detail: event }));

  if (provider === "vercel") {
    trackVercel(name, event.properties);
  }

  if (provider === "openpanel" && openPanelClientId) {
    window.op?.("track", name, event.properties);
  }

  if (debug) {
    console.info("[analytics]", event.name, event.properties);
  }
}
