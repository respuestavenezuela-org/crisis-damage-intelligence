"use client";

import { useEffect } from "react";
import type { AnalyticsEventName, AnalyticsProperties } from "@/lib/analytics";
import { trackAnalytics } from "@/lib/analytics";

function eventFromHref(anchor: HTMLAnchorElement): AnalyticsEventName | undefined {
  const href = anchor.getAttribute("href") ?? "";
  const lower = href.toLowerCase();
  if (lower.includes("google.") && lower.includes("/maps")) return "google_maps_link_clicked";
  if (lower.includes("/data/chips/")) return "evidence_chip_clicked";
  if (lower.endsWith(".csv") || lower.endsWith(".geojson") || lower.endsWith(".kml")) return "data_download_clicked";
  return undefined;
}

function formatFromHref(anchor: HTMLAnchorElement) {
  const href = anchor.getAttribute("href") ?? "";
  const match = href.toLowerCase().match(/\.([a-z0-9]+)(?:[?#].*)?$/);
  return match?.[1];
}

export default function AnalyticsEvents() {
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      const anchor = target.closest("a");
      if (!(anchor instanceof HTMLAnchorElement)) return;

      const name = (anchor.dataset.analyticsEvent as AnalyticsEventName | undefined) ?? eventFromHref(anchor);
      if (!name) return;

      const properties: AnalyticsProperties = {
        aoi_id: anchor.dataset.analyticsAoi,
        format: anchor.dataset.analyticsFormat ?? formatFromHref(anchor),
        surface: anchor.dataset.analyticsSurface,
        chip_kind: anchor.dataset.analyticsChipKind,
        has_vlm: anchor.dataset.analyticsHasVlm ? anchor.dataset.analyticsHasVlm === "true" : undefined,
      };

      trackAnalytics(name, properties);
    };

    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, []);

  return null;
}
