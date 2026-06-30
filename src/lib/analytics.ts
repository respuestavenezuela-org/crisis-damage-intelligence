"use client";

import { track as trackVercel } from "@vercel/analytics";

export type AnalyticsEventName =
  | "app_loaded"
  | "language_switched"
  | "aoi_selected"
  | "imagery_mode_changed"
  | "basemap_changed"
  | "damage_filter_changed"
  | "priority_item_clicked"
  | "google_maps_link_clicked"
  | "translator_open"
  | "translator_telegram"
  | "data_download_clicked"
  | "evidence_chip_clicked"
  | "map_ready"
  | "first_tile_loaded"
  | "first_interaction_seconds";

export type AnalyticsProperty = string | number | boolean | null | undefined;
export type AnalyticsProperties = Record<string, AnalyticsProperty>;

export type AnalyticsEvent = {
  name: AnalyticsEventName;
  properties: Record<string, Exclude<AnalyticsProperty, undefined>>;
};

declare global {
  interface Window {
    crisisDamageAnalytics?: {
      track: (event: AnalyticsEvent) => void;
    };
    crisisDamageAnalyticsQueue?: AnalyticsEvent[];
  }
}

const provider = process.env.NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER ?? "openpanel";
const openPanelClientId = process.env.NEXT_PUBLIC_OPENPANEL_CLIENT_ID;
const debug = process.env.NEXT_PUBLIC_ANALYTICS_DEBUG === "true";

function compactProperties(properties: AnalyticsProperties = {}) {
  return Object.fromEntries(
    Object.entries(properties).filter(([, value]) => value !== undefined),
  ) as AnalyticsEvent["properties"];
}

export function trackAnalytics(name: AnalyticsEventName, properties: AnalyticsProperties = {}) {
  if (typeof window === "undefined") return;

  const event: AnalyticsEvent = {
    name,
    properties: compactProperties(properties),
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
