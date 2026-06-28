"use client";

import { useCallback, useEffect, useRef } from "react";
import OlMap from "ol/Map.js";
import View from "ol/View.js";
import GeoJSON from "ol/format/GeoJSON.js";
import Feature from "ol/Feature.js";
import Overlay from "ol/Overlay.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import WebGLTileLayer from "ol/layer/WebGLTile.js";
import OSM from "ol/source/OSM.js";
import XYZ from "ol/source/XYZ.js";
import GeoTIFF from "ol/source/GeoTIFF.js";
import VectorSource from "ol/source/Vector.js";
import { Fill, Stroke, Style } from "ol/style.js";
import CircleStyle from "ol/style/Circle.js";
import { fromLonLat, toLonLat } from "ol/proj.js";
import { boundingExtent, getCenter } from "ol/extent.js";
import "ol/ol.css";
import type { AoiRecord, DamageFeature, VlmRecord } from "../types";

declare global {
  interface Window {
    __damageMapDebug?: {
      visibleFeatures: string[];
      selectedId?: string;
      center?: { lat: number; lng: number };
      zoom?: number;
      filter: Props["filter"];
      mode: Props["mode"];
      basemap: Props["basemap"];
      raster?: "before" | "after" | "none";
    };
  }
}

type Props = {
  aoi: AoiRecord;
  features: DamageFeature[];
  mode: "before" | "after";
  opacity: number;
  filter: "all" | "severe" | "vlm";
  basemap: "map" | "aerial";
  vlm: Record<string, VlmRecord>;
  selectedId?: string;
  focusToken: number;
  aoiFocusToken: number;
  onSelect: (feature: DamageFeature | null) => void;
};

type OlDamageFeature = Feature & { original?: DamageFeature };
type RasterLayer = WebGLTileLayer | TileLayer<XYZ>;
type InteriorGeometry = {
  getType: () => string;
  getCoordinates?: () => unknown;
  getInteriorPoint?: () => { getCoordinates: () => number[] };
  getInteriorPoints?: () => { getCoordinates: () => number[][] };
  intersectsCoordinate?: (coordinate: number[]) => boolean;
};

function damageClass(properties: DamageFeature["properties"]) {
  const raw = String(properties.damage_class ?? properties.damage_gra ?? properties.confirmed_damage_class ?? "").toLowerCase();
  if (raw.includes("possibly")) return "possible";
  if (raw.includes("destroy") || raw.includes("major") || raw.includes("damaged") || raw === "major_damage") return "severe";
  if (raw.includes("minor") || raw.includes("possible")) return "possible";
  if (raw.includes("uncertain")) return "uncertain";
  return "low";
}

function colorFor(kind: string) {
  if (kind === "severe") return "#c42128";
  if (kind === "possible") return "#d78a1f";
  if (kind === "uncertain") return "#64748b";
  return "#7a7f87";
}

function focusCoordinate(feature: OlDamageFeature, original: DamageFeature) {
  const geometry = feature.getGeometry() as InteriorGeometry | undefined;
  const centroidLat = Number(original.properties.centroid_lat);
  const centroidLon = Number(original.properties.centroid_lon);
  if (Number.isFinite(centroidLat) && Number.isFinite(centroidLon)) {
    const candidate = fromLonLat([centroidLon, centroidLat]);
    if (!geometry?.intersectsCoordinate || geometry.intersectsCoordinate(candidate)) return candidate;
  }
  if (geometry?.getType() === "Polygon" && geometry.getInteriorPoint) {
    return geometry.getInteriorPoint().getCoordinates().slice(0, 2);
  }
  if (geometry?.getType() === "MultiPolygon" && geometry.getInteriorPoints) {
    const points = geometry.getInteriorPoints().getCoordinates();
    if (points[0]) return points[0].slice(0, 2);
  }
  const extent = feature.getGeometry()?.getExtent();
  return extent ? getCenter(extent) : undefined;
}

function passesFilter(feature: DamageFeature, filter: Props["filter"], vlm: Record<string, VlmRecord>) {
  const id = feature.properties.id;
  if (filter === "vlm") return Boolean(vlm[id]);
  if (filter === "severe") return damageClass(feature.properties) === "severe";
  return true;
}

export default function MapPanel({ aoi, features, mode, opacity, filter, basemap, vlm, selectedId, focusToken, aoiFocusToken, onSelect }: Props) {
  const nodeRef = useRef<HTMLDivElement | null>(null);
  const popupRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<OlMap | null>(null);
  const baseRef = useRef<TileLayer<OSM> | null>(null);
  const aerialBaseRef = useRef<TileLayer<XYZ> | null>(null);
  const beforeRef = useRef<RasterLayer | null>(null);
  const afterRef = useRef<RasterLayer | null>(null);
  const vectorRef = useRef<VectorLayer<VectorSource> | null>(null);
  const highlightRef = useRef<VectorLayer<VectorSource> | null>(null);
  const markerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const popupOverlayRef = useRef<Overlay | null>(null);
  const featuresRef = useRef<DamageFeature[]>([]);
  const olFeatureByIdRef = useRef<Map<string, OlDamageFeature>>(new Map());
  const modeRef = useRef(mode);
  const selectedIdRef = useRef(selectedId);
  const renderVectorsRef = useRef<() => void>(() => {});

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  useEffect(() => {
    featuresRef.current = features;
    renderVectorsRef.current();
  }, [features]);

  const setDebug = useCallback((visibleFeatures: DamageFeature[]) => {
    const map = mapRef.current;
    if (!map) return;
    const [lng, lat] = toLonLat(map.getView().getCenter() ?? [0, 0]);
    window.__damageMapDebug = {
      visibleFeatures: visibleFeatures.map((feature) => feature.properties.id),
      selectedId: selectedIdRef.current,
      center: { lat, lng },
      zoom: map.getView().getZoom(),
      filter,
      mode: modeRef.current,
      basemap,
      raster: afterRef.current?.getVisible() ? "after" : beforeRef.current?.getVisible() ? "before" : "none",
    };
  }, [basemap, filter]);

  const styleFor = useCallback((feature: OlDamageFeature) => {
    const original = feature.original;
    if (!original) return undefined;
    const kind = damageClass(original.properties);
    const color = colorFor(kind);
    if (feature.getGeometry()?.getType() === "Point") {
      return new Style({
        image: new CircleStyle({
          radius: kind === "severe" ? 7 : 5,
          stroke: new Stroke({ color: hexToRgba(color, opacity), width: 2 }),
          fill: new Fill({ color: hexToRgba(color, Math.max(0.45, opacity)) }),
        }),
      });
    }
    return new Style({
      stroke: new Stroke({ color: hexToRgba(color, opacity), width: kind === "low" ? 1 : 2 }),
      fill: new Fill({ color: hexToRgba(color, opacity) }),
    });
  }, [opacity]);

  const focusFeature = useCallback((id?: string) => {
    const map = mapRef.current;
    if (!map) return;
    if (!id) {
      highlightRef.current?.getSource()?.clear();
      markerRef.current?.getSource()?.clear();
      popupOverlayRef.current?.setPosition(undefined);
      if (popupRef.current) popupRef.current.innerHTML = "";
      nodeRef.current?.setAttribute("data-focused-id", "");
      setDebug(featuresRef.current.filter((candidate) => passesFilter(candidate, filter, vlm)));
      return;
    }
    const feature = featuresRef.current.find((candidate) => candidate.properties.id === id);
    let olFeature = olFeatureByIdRef.current.get(id);
    if (!feature) return;
    if (!olFeature) {
      olFeature = new GeoJSON().readFeature(feature, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      }) as OlDamageFeature;
      olFeature.original = feature;
    }
    const center = focusCoordinate(olFeature, feature);
    if (!center) return;
    map.getView().setCenter(center);
    map.getView().setZoom(18);
    highlightRef.current?.getSource()?.clear();
    if (olFeature.getGeometry()) {
      const highlightFeature = olFeature.clone() as OlDamageFeature;
      highlightFeature.original = feature;
      highlightRef.current?.getSource()?.addFeature(highlightFeature);
    }
    highlightRef.current?.setStyle(new Style({
      stroke: new Stroke({ color: "#ffffff", width: 5 }),
      fill: new Fill({ color: "rgba(255,255,255,0.08)" }),
    }));
    markerRef.current?.getSource()?.clear();
    const markerFeature = new Feature({ geometry: new GeoJSON().readGeometry({ type: "Point", coordinates: toLonLat(center) }, { dataProjection: "EPSG:4326", featureProjection: "EPSG:3857" }) });
    markerRef.current?.getSource()?.addFeature(markerFeature);
    markerRef.current?.setStyle(new Style({
      image: new CircleStyle({
        radius: 10,
        stroke: new Stroke({ color: "#ffffff", width: 3 }),
        fill: new Fill({ color: "rgba(196,33,40,0.28)" }),
      }),
    }));
    if (popupRef.current) {
      popupRef.current.innerHTML = popupHtml(feature.properties);
      popupOverlayRef.current?.setPosition(center);
    }
    const [lng, lat] = toLonLat(center);
    nodeRef.current?.setAttribute("data-focused-id", id);
    nodeRef.current?.setAttribute("data-map-center", `${lat.toFixed(7)},${lng.toFixed(7)}`);
    nodeRef.current?.setAttribute("data-map-zoom", String(map.getView().getZoom()));
    setDebug(featuresRef.current.filter((candidate) => passesFilter(candidate, filter, vlm)));
  }, [filter, setDebug, vlm]);

  const renderVectors = useCallback(() => {
    const vector = vectorRef.current;
    if (!vector) return;
    const source = vector.getSource();
    if (!source) return;
    const visible = featuresRef.current.filter((feature) => passesFilter(feature, filter, vlm));
    const olFeatures = new GeoJSON().readFeatures({ type: "FeatureCollection", features: visible }, {
      dataProjection: "EPSG:4326",
      featureProjection: "EPSG:3857",
    }) as OlDamageFeature[];
    olFeatureByIdRef.current.clear();
    olFeatures.forEach((feature, index) => {
      feature.original = visible[index];
      olFeatureByIdRef.current.set(visible[index].properties.id, feature);
    });
    source.clear();
    source.addFeatures(olFeatures);
    vector.setStyle((feature) => styleFor(feature as OlDamageFeature));
    nodeRef.current?.setAttribute("data-visible-features", String(visible.length));
    setDebug(visible);
  }, [filter, setDebug, styleFor, vlm]);

  useEffect(() => {
    renderVectorsRef.current = renderVectors;
  }, [renderVectors]);

  useEffect(() => {
    if (!nodeRef.current || mapRef.current) return;
    const base = new TileLayer({ source: new OSM(), visible: true });
    const aerialBase = new TileLayer({
      source: new XYZ({
        attributions: "Tiles © Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        crossOrigin: "anonymous",
        maxZoom: 19,
      }),
      visible: false,
      zIndex: 1,
    });
    const vector = new VectorLayer({ source: new VectorSource(), zIndex: 30 });
    const highlight = new VectorLayer({ source: new VectorSource(), zIndex: 40 });
    const marker = new VectorLayer({ source: new VectorSource(), zIndex: 50 });
    const popup = new Overlay({ element: popupRef.current ?? undefined, autoPan: { animation: { duration: 0 } }, offset: [0, -12] });
    const map = new OlMap({
      target: nodeRef.current,
      layers: [base, aerialBase, vector, highlight, marker],
      overlays: [popup],
      view: new View({ center: fromLonLat([aoi.center[1], aoi.center[0]]), zoom: 12 }),
      controls: [],
    });
    baseRef.current = base;
    aerialBaseRef.current = aerialBase;
    vectorRef.current = vector;
    highlightRef.current = highlight;
    markerRef.current = marker;
    popupOverlayRef.current = popup;
    mapRef.current = map;

    map.on("singleclick", (event) => {
      const hit = map.forEachFeatureAtPixel(event.pixel, (feature) => feature as OlDamageFeature, {
        layerFilter: (layer) => layer === vectorRef.current,
      });
      if (hit?.original) onSelect(hit.original);
      else onSelect(null);
    });

    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
    };
  }, [aoi.center, onSelect]);

  useEffect(() => {
    baseRef.current?.setVisible(basemap === "map");
    aerialBaseRef.current?.setVisible(basemap === "aerial");
    setDebug(featuresRef.current.filter((feature) => passesFilter(feature, filter, vlm)));
  }, [basemap, filter, setDebug, vlm]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (beforeRef.current) map.removeLayer(beforeRef.current);
    if (afterRef.current) map.removeLayer(afterRef.current);
    beforeRef.current = null;
    afterRef.current = null;
    highlightRef.current?.getSource()?.clear();
    markerRef.current?.getSource()?.clear();
    popupOverlayRef.current?.setPosition(undefined);

    if (aoi.layers.beforeTiles || aoi.layers.beforeImage) {
      beforeRef.current = aoi.layers.beforeTiles
        ? new TileLayer({
          source: new XYZ({ url: aoi.layers.beforeTiles, maxZoom: 18, minZoom: 12, transition: 0 }),
          opacity: 1,
          visible: modeRef.current === "before",
          zIndex: 10,
        })
        : new WebGLTileLayer({
          source: new GeoTIFF({ sources: [{ url: aoi.layers.beforeImage as string }], convertToRGB: "auto" }),
          opacity: 1,
          visible: modeRef.current === "before",
          zIndex: 10,
        });
      map.addLayer(beforeRef.current);
    }
    if (aoi.layers.afterTiles || aoi.layers.afterImage) {
      afterRef.current = aoi.layers.afterTiles
        ? new TileLayer({
          source: new XYZ({ url: aoi.layers.afterTiles, maxZoom: 18, minZoom: 12, transition: 0 }),
          opacity: 1,
          visible: modeRef.current === "after",
          zIndex: 11,
        })
        : new WebGLTileLayer({
          source: new GeoTIFF({ sources: [{ url: aoi.layers.afterImage as string }], convertToRGB: "auto" }),
          opacity: 1,
          visible: modeRef.current === "after",
          zIndex: 11,
        });
      map.addLayer(afterRef.current);
    }

    const bounds3857 = boundingExtent([
      fromLonLat([aoi.bounds[0][1], aoi.bounds[0][0]]),
      fromLonLat([aoi.bounds[1][1], aoi.bounds[1][0]]),
    ]);
    map.getView().fit(bounds3857, { padding: [60, 60, 60, 60], duration: 0, maxZoom: 15 });
    renderVectorsRef.current();
  }, [aoi]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const bounds3857 = boundingExtent([
      fromLonLat([aoi.bounds[0][1], aoi.bounds[0][0]]),
      fromLonLat([aoi.bounds[1][1], aoi.bounds[1][0]]),
    ]);
    map.getView().fit(bounds3857, { padding: [60, 60, 60, 60], duration: 0, maxZoom: 15 });
  }, [aoi.bounds, aoiFocusToken]);

  useEffect(() => {
    renderVectors();
  }, [renderVectors]);

  useEffect(() => {
    const hasBefore = Boolean(aoi.layers.beforeTiles || aoi.layers.beforeImage);
    const hasAfter = Boolean(aoi.layers.afterTiles || aoi.layers.afterImage);
    beforeRef.current?.setVisible(mode === "before" && hasBefore);
    afterRef.current?.setVisible(mode === "after" && hasAfter);
    if (!hasBefore && mode === "before") afterRef.current?.setVisible(false);
    setDebug(featuresRef.current.filter((feature) => passesFilter(feature, filter, vlm)));
  }, [aoi.layers.afterImage, aoi.layers.afterTiles, aoi.layers.beforeImage, aoi.layers.beforeTiles, filter, mode, setDebug, vlm]);

  useEffect(() => {
    focusFeature(selectedId);
  }, [focusFeature, focusToken, selectedId]);

  return (
    <>
      <div ref={nodeRef} className="map-node" data-filter={filter} data-mode={mode} data-basemap={basemap} data-opacity={opacity} data-selected-id={selectedId ?? ""} />
      <div ref={popupRef} className="ol-popup" />
    </>
  );
}

function hexToRgba(hex: string, alpha: number) {
  const value = hex.replace("#", "");
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

function escapeHtml(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function popupHtml(p: DamageFeature["properties"]) {
  const mapsUrl = typeof p.google_maps_url === "string" ? p.google_maps_url : "";
  const label = p.not_official_ems ? "External" : "EMS";
  const id = String(p.source_feature_id ?? p.id);
  const aoiId = String(p.aoi_id ?? "");
  const damage = String(p.damage_gra ?? p.damage_class ?? "unknown");
  const percent = String(p.damage_percent ?? p.damage_score ?? "-");
  return (
    `<strong>${escapeHtml(id)}</strong>` +
    `<span>${label}: ${escapeHtml(damage)} · ${escapeHtml(percent)}%</span>` +
    (mapsUrl ? `<a href="${escapeHtml(mapsUrl)}" target="_blank" rel="noreferrer" data-analytics-event="google_maps_link_clicked" data-analytics-aoi="${escapeHtml(aoiId)}" data-analytics-surface="map_popup">Google Maps</a>` : "")
  );
}
