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
import type { AoiRecord, DamageFeature, OperationalSignalFeature, VlmRecord } from "../types";
import { featureInspectionPoint } from "./feature-location";

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
      visibleSignals?: string[];
      selectedSignalId?: string;
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
  operationalSignals: OperationalSignalFeature[];
  showOperationalSignals: boolean;
  selectedId?: string;
  selectedSignalId?: string;
  focusToken: number;
  aoiFocusToken: number;
  onMapReady: (payload: { aoi_id: string; feature_count: number; mode: Props["mode"]; basemap: Props["basemap"] }) => void;
  onFirstTileLoaded: (payload: { aoi_id: string; layer: string; mode: Props["mode"]; basemap: Props["basemap"] }) => void;
  onLayerLoadFailed: (payload: { aoi_id: string; layer: string; status: "error"; mode: Props["mode"]; basemap: Props["basemap"]; surface: string }) => void;
  onSelect: (feature: DamageFeature | null) => void;
  onSelectSignal: (feature: OperationalSignalFeature | null) => void;
};

type OlDamageFeature = Feature & { original?: DamageFeature };
type OlSignalFeature = Feature & { signal?: OperationalSignalFeature };
type RasterLayer = WebGLTileLayer | TileLayer<XYZ>;
const DIRECT_RASTER_MOBILE_MAX_BYTES = 250_000_000;
type InteriorGeometry = {
  getType: () => string;
  getCoordinates?: () => unknown;
  getInteriorPoint?: () => { getCoordinates: () => number[] };
  getInteriorPoints?: () => { getCoordinates: () => number[][] };
  intersectsCoordinate?: (coordinate: number[]) => boolean;
};

function damageClass(properties: DamageFeature["properties"]) {
  const raw = String(properties.damage_class ?? properties.damage_gra ?? properties.confirmed_damage_class ?? "").toLowerCase();
  if (raw.includes("visual_confirmed_gap")) return "severe";
  if (raw.includes("needs_human_review")) return "possible";
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
  const inspectionPoint = featureInspectionPoint(original);
  if (inspectionPoint) return fromLonLat([inspectionPoint.lon, inspectionPoint.lat]);
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

function directRasterIsMobileSafe(bytes?: number | null) {
  return !bytes || bytes <= DIRECT_RASTER_MOBILE_MAX_BYTES;
}

function canRenderBeforeImage(aoi: AoiRecord) {
  return Boolean(aoi.layers.beforeImage && directRasterIsMobileSafe(aoi.imagery?.before?.bytes));
}

function canRenderAfterImage(aoi: AoiRecord) {
  return Boolean(aoi.layers.afterImage && directRasterIsMobileSafe(aoi.imagery?.after?.bytes));
}

function hasBeforeLayer(aoi: AoiRecord) {
  return Boolean(aoi.layers.beforeTiles || canRenderBeforeImage(aoi) || aoi.imagery?.approximateReference?.urlTemplate);
}

export default function MapPanel({
  aoi,
  features,
  mode,
  opacity,
  filter,
  basemap,
  vlm,
  operationalSignals,
  showOperationalSignals,
  selectedId,
  selectedSignalId,
  focusToken,
  aoiFocusToken,
  onMapReady,
  onFirstTileLoaded,
  onLayerLoadFailed,
  onSelect,
  onSelectSignal,
}: Props) {
  const nodeRef = useRef<HTMLDivElement | null>(null);
  const popupRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<OlMap | null>(null);
  const baseRef = useRef<TileLayer<OSM> | null>(null);
  const aerialBaseRef = useRef<TileLayer<XYZ> | null>(null);
  const beforeRef = useRef<RasterLayer | null>(null);
  const afterRef = useRef<RasterLayer | null>(null);
  const signalRef = useRef<VectorLayer<VectorSource> | null>(null);
  const vectorRef = useRef<VectorLayer<VectorSource> | null>(null);
  const highlightRef = useRef<VectorLayer<VectorSource> | null>(null);
  const markerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const popupOverlayRef = useRef<Overlay | null>(null);
  const featuresRef = useRef<DamageFeature[]>([]);
  const signalsRef = useRef<OperationalSignalFeature[]>([]);
  const aoiIdRef = useRef(aoi.id);
  const olFeatureByIdRef = useRef<Map<string, OlDamageFeature>>(new Map());
  const olSignalByIdRef = useRef<Map<string, OlSignalFeature>>(new Map());
  const modeRef = useRef(mode);
  const selectedIdRef = useRef(selectedId);
  const selectedSignalIdRef = useRef(selectedSignalId);
  const showOperationalSignalsRef = useRef(showOperationalSignals);
  const onSelectRef = useRef(onSelect);
  const onSelectSignalRef = useRef(onSelectSignal);
  const onMapReadyRef = useRef(onMapReady);
  const onFirstTileLoadedRef = useRef(onFirstTileLoaded);
  const onLayerLoadFailedRef = useRef(onLayerLoadFailed);
  const renderVectorsRef = useRef<() => void>(() => {});
  const renderSignalsRef = useRef<() => void>(() => {});
  const tileTrackedRef = useRef<Set<string>>(new Set());
  const tileFailureTrackedRef = useRef<Set<string>>(new Set());
  const basemapRef = useRef(basemap);

  useEffect(() => {
    onMapReadyRef.current = onMapReady;
  }, [onMapReady]);

  useEffect(() => {
    onFirstTileLoadedRef.current = onFirstTileLoaded;
  }, [onFirstTileLoaded]);

  useEffect(() => {
    onLayerLoadFailedRef.current = onLayerLoadFailed;
  }, [onLayerLoadFailed]);

  useEffect(() => {
    aoiIdRef.current = aoi.id;
  }, [aoi.id]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    onSelectSignalRef.current = onSelectSignal;
  }, [onSelectSignal]);

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    basemapRef.current = basemap;
  }, [basemap]);

  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  useEffect(() => {
    selectedSignalIdRef.current = selectedSignalId;
  }, [selectedSignalId]);

  useEffect(() => {
    showOperationalSignalsRef.current = showOperationalSignals;
    renderSignalsRef.current();
  }, [showOperationalSignals]);

  useEffect(() => {
    featuresRef.current = features;
    renderVectorsRef.current();
  }, [features]);

  useEffect(() => {
    signalsRef.current = operationalSignals;
    renderSignalsRef.current();
  }, [operationalSignals]);

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
      visibleSignals: showOperationalSignalsRef.current ? signalsRef.current.map((signal) => signal.properties.id) : [],
      selectedSignalId: selectedSignalIdRef.current,
    };
  }, [basemap, filter]);

  const signalStyleFor = useCallback((feature: OlSignalFeature) => {
    const priority = feature.signal?.properties.priority ?? "low";
    const color = priority === "high" ? "#4c3b82" : priority === "medium" ? "#c77700" : "#42635b";
    const alpha = priority === "high" ? 0.34 : priority === "medium" ? 0.28 : 0.18;
    return new Style({
      stroke: new Stroke({ color: hexToRgba(color, 0.92), width: priority === "high" ? 2.5 : 1.5 }),
      fill: new Fill({ color: hexToRgba(color, alpha) }),
    });
  }, []);

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
      nodeRef.current?.setAttribute("data-focused-internal-id", "");
      setDebug(featuresRef.current.filter((candidate) => candidate.properties.aoi_id === aoi.id && passesFilter(candidate, filter, vlm)));
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
      popupRef.current.innerHTML = popupHtml(feature);
      popupOverlayRef.current?.setPosition(center);
    }
    const [lng, lat] = toLonLat(center);
    nodeRef.current?.setAttribute("data-focused-id", String(feature.properties.source_feature_id ?? id));
    nodeRef.current?.setAttribute("data-focused-internal-id", id);
    nodeRef.current?.setAttribute("data-focused-signal-id", "");
    nodeRef.current?.setAttribute("data-map-center", `${lat.toFixed(7)},${lng.toFixed(7)}`);
    nodeRef.current?.setAttribute("data-map-zoom", String(map.getView().getZoom()));
    setDebug(featuresRef.current.filter((candidate) => candidate.properties.aoi_id === aoi.id && passesFilter(candidate, filter, vlm)));
  }, [aoi.id, filter, setDebug, vlm]);

  const focusSignal = useCallback((id?: string) => {
    const map = mapRef.current;
    if (!map) return;
    if (!id) {
      if (!selectedIdRef.current) {
        highlightRef.current?.getSource()?.clear();
        markerRef.current?.getSource()?.clear();
        popupOverlayRef.current?.setPosition(undefined);
        if (popupRef.current) popupRef.current.innerHTML = "";
        nodeRef.current?.setAttribute("data-focused-signal-id", "");
      }
      return;
    }
    const signal = signalsRef.current.find((candidate) => candidate.properties.id === id);
    let olSignal = olSignalByIdRef.current.get(id);
    if (!signal) return;
    if (!olSignal) {
      olSignal = new GeoJSON().readFeature(signal, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      }) as OlSignalFeature;
      olSignal.signal = signal;
    }
    const geometry = olSignal.getGeometry();
    if (!geometry) return;
    map.getView().fit(geometry.getExtent(), { padding: [80, 80, 80, 80], duration: 0, maxZoom: 13 });
    const [lng, lat] = toLonLat(getCenter(geometry.getExtent()));
    highlightRef.current?.getSource()?.clear();
    const highlightFeature = olSignal.clone() as OlSignalFeature;
    highlightFeature.signal = signal;
    highlightRef.current?.getSource()?.addFeature(highlightFeature);
    highlightRef.current?.setStyle(new Style({
      stroke: new Stroke({ color: "#ffffff", width: 5 }),
      fill: new Fill({ color: "rgba(255,255,255,0.10)" }),
    }));
    markerRef.current?.getSource()?.clear();
    popupOverlayRef.current?.setPosition(undefined);
    if (popupRef.current) {
      popupRef.current.innerHTML = signalPopupHtml(signal.properties);
      popupOverlayRef.current?.setPosition(getCenter(geometry.getExtent()));
    }
    nodeRef.current?.setAttribute("data-focused-id", "");
    nodeRef.current?.setAttribute("data-focused-internal-id", "");
    nodeRef.current?.setAttribute("data-focused-signal-id", id);
    nodeRef.current?.setAttribute("data-map-center", `${lat.toFixed(7)},${lng.toFixed(7)}`);
    nodeRef.current?.setAttribute("data-map-zoom", String(map.getView().getZoom()));
  }, []);

  const renderSignals = useCallback(() => {
    const vector = signalRef.current;
    if (!vector) return;
    const source = vector.getSource();
    if (!source) return;
    const visible = showOperationalSignalsRef.current ? signalsRef.current : [];
    const olFeatures = new GeoJSON().readFeatures({ type: "FeatureCollection", features: visible }, {
      dataProjection: "EPSG:4326",
      featureProjection: "EPSG:3857",
    }) as OlSignalFeature[];
    olSignalByIdRef.current.clear();
    olFeatures.forEach((feature, index) => {
      feature.signal = visible[index];
      olSignalByIdRef.current.set(visible[index].properties.id, feature);
    });
    source.clear();
    source.addFeatures(olFeatures);
    vector.setStyle((feature) => signalStyleFor(feature as OlSignalFeature));
    nodeRef.current?.setAttribute("data-visible-signals", String(visible.length));
    setDebug(featuresRef.current.filter((candidate) => candidate.properties.aoi_id === aoi.id && passesFilter(candidate, filter, vlm)));
  }, [aoi.id, filter, setDebug, signalStyleFor, vlm]);

  useEffect(() => {
    renderSignalsRef.current = renderSignals;
  }, [renderSignals]);

  const renderVectors = useCallback(() => {
    const vector = vectorRef.current;
    if (!vector) return;
    const source = vector.getSource();
    if (!source) return;
    const visible = featuresRef.current.filter((feature) => feature.properties.aoi_id === aoi.id && passesFilter(feature, filter, vlm));
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
    onMapReadyRef.current({
      aoi_id: aoi.id,
      feature_count: visible.length,
      mode: modeRef.current,
      basemap,
    });
  }, [aoi.id, basemap, filter, setDebug, styleFor, vlm]);

  useEffect(() => {
    renderVectorsRef.current = renderVectors;
  }, [renderVectors]);

  const applyLayerVisibility = useCallback((nextMode: Props["mode"], nextBasemap: Props["basemap"]) => {
    const map = mapRef.current;
    const hasBefore = hasBeforeLayer(aoi);
    const hasAfter = Boolean(aoi.layers.afterTiles || canRenderAfterImage(aoi));
    baseRef.current?.setVisible(nextBasemap === "map");
    aerialBaseRef.current?.setVisible(nextBasemap === "aerial");
    beforeRef.current?.setVisible(nextMode === "before" && hasBefore);
    afterRef.current?.setVisible(nextMode === "after" && hasAfter);
    map?.renderSync();
  }, [aoi]);

  const attachFirstTileTracker = useCallback((source: unknown, layer: string) => {
    const aoiId = aoiIdRef.current;
    const key = `${aoiId}:${layer}`;
    if (!source || tileTrackedRef.current.has(key)) return;
    const maybeSource = source as {
      once?: (event: string, listener: () => void) => void;
      on?: (event: string, listener: () => void) => void;
    };
    const listener = () => {
      if (tileTrackedRef.current.has(key)) return;
      tileTrackedRef.current.add(key);
      onFirstTileLoadedRef.current({
        aoi_id: aoiId,
        layer,
        mode: modeRef.current,
        basemap: basemapRef.current,
      });
    };
    const errorListener = () => {
      if (tileFailureTrackedRef.current.has(key)) return;
      tileFailureTrackedRef.current.add(key);
      onLayerLoadFailedRef.current({
        aoi_id: aoiId,
        layer,
        status: "error",
        mode: modeRef.current,
        basemap: basemapRef.current,
        surface: "map_layer",
      });
    };
    if (maybeSource.once) {
      maybeSource.once("tileloadend", listener);
      maybeSource.once("imageloadend", listener);
      maybeSource.once("change", listener);
      maybeSource.once("tileloaderror", errorListener);
      maybeSource.once("imageloaderror", errorListener);
      maybeSource.once("error", errorListener);
    } else if (maybeSource.on) {
      maybeSource.on("change", listener);
      maybeSource.on("error", errorListener);
    }
  }, []);

  useEffect(() => {
    if (!nodeRef.current || mapRef.current) return;
    const base = new TileLayer({ source: new OSM(), visible: basemapRef.current === "map", zIndex: 0 });
    const aerialBase = new TileLayer({
      source: new XYZ({
        attributions: "Tiles © Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        crossOrigin: "anonymous",
        maxZoom: 19,
      }),
      visible: basemapRef.current === "aerial",
      zIndex: 0,
    });
    const signal = new VectorLayer({ source: new VectorSource(), zIndex: 20 });
    const vector = new VectorLayer({ source: new VectorSource(), zIndex: 30 });
    const highlight = new VectorLayer({ source: new VectorSource(), zIndex: 40 });
    const marker = new VectorLayer({ source: new VectorSource(), zIndex: 50 });
    const popupElement = document.createElement("div");
    popupElement.className = "ol-popup";
    popupRef.current = popupElement;
    const popup = new Overlay({ element: popupElement, autoPan: { animation: { duration: 0 } }, offset: [0, -12] });
    const map = new OlMap({
      target: nodeRef.current,
      layers: [base, aerialBase, signal, vector, highlight, marker],
      overlays: [popup],
      view: new View({ center: fromLonLat([aoi.center[1], aoi.center[0]]), zoom: 12 }),
      controls: [],
    });
    baseRef.current = base;
    aerialBaseRef.current = aerialBase;
    signalRef.current = signal;
    vectorRef.current = vector;
    highlightRef.current = highlight;
    markerRef.current = marker;
    popupOverlayRef.current = popup;
    mapRef.current = map;
    attachFirstTileTracker(base.getSource(), "base_map");
    attachFirstTileTracker(aerialBase.getSource(), "base_aerial");

    map.on("singleclick", (event) => {
      const hit = map.forEachFeatureAtPixel(event.pixel, (feature) => feature as OlDamageFeature, {
        layerFilter: (layer) => layer === vectorRef.current,
      });
      if (hit?.original) {
        onSelectSignalRef.current(null);
        onSelectRef.current(hit.original);
        return;
      }
      const signalHit = map.forEachFeatureAtPixel(event.pixel, (feature) => feature as OlSignalFeature, {
        layerFilter: (layer) => layer === signalRef.current,
      });
      if (signalHit?.signal) {
        onSelectSignalRef.current(signalHit.signal);
        return;
      }
      onSelectSignalRef.current(null);
      onSelectRef.current(null);
    });

    return () => {
      popup.setElement(undefined);
      popupElement.remove();
      popupRef.current = null;
      map.setTarget(undefined);
      signalRef.current = null;
      mapRef.current = null;
    };
  }, [aoi.center, attachFirstTileTracker]);

  useEffect(() => {
    applyLayerVisibility(modeRef.current, basemap);
    setDebug(featuresRef.current.filter((feature) => feature.properties.aoi_id === aoi.id && passesFilter(feature, filter, vlm)));
  }, [aoi.id, applyLayerVisibility, basemap, filter, setDebug, vlm]);

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

    const bounds3857 = boundingExtent([
      fromLonLat([aoi.bounds[0][1], aoi.bounds[0][0]]),
      fromLonLat([aoi.bounds[1][1], aoi.bounds[1][0]]),
    ]);

    const beforeImageUrl = canRenderBeforeImage(aoi) ? aoi.layers.beforeImage : undefined;
    const afterImageUrl = canRenderAfterImage(aoi) ? aoi.layers.afterImage : undefined;

    if (aoi.layers.beforeTiles || beforeImageUrl || aoi.imagery?.approximateReference?.urlTemplate) {
      beforeRef.current = aoi.layers.beforeTiles
        ? new TileLayer({
          source: new XYZ({ url: aoi.layers.beforeTiles, maxZoom: 18, minZoom: 12, transition: 0 }),
          extent: bounds3857,
          opacity: 1,
          visible: modeRef.current === "before",
          zIndex: 10,
        })
        : beforeImageUrl
          ? new WebGLTileLayer({
          source: new GeoTIFF({ sources: [{ url: beforeImageUrl }], convertToRGB: "auto" }),
          opacity: 1,
          visible: modeRef.current === "before",
          zIndex: 10,
        })
          : new TileLayer({
          source: new XYZ({
            attributions: aoi.imagery?.approximateReference?.source ?? "Reference imagery",
            url: aoi.imagery?.approximateReference?.urlTemplate,
            crossOrigin: "anonymous",
            maxZoom: 19,
            transition: 0,
          }),
          opacity: 1,
          visible: modeRef.current === "before",
          zIndex: 10,
        });
      map.addLayer(beforeRef.current);
      attachFirstTileTracker(beforeRef.current.getSource(), "before");
    }
    if (aoi.layers.afterTiles || afterImageUrl) {
      afterRef.current = aoi.layers.afterTiles
        ? new TileLayer({
          source: new XYZ({ url: aoi.layers.afterTiles, maxZoom: 18, minZoom: 12, transition: 0 }),
          extent: bounds3857,
          opacity: 1,
          visible: modeRef.current === "after",
          zIndex: 11,
        })
        : new WebGLTileLayer({
          source: new GeoTIFF({ sources: [{ url: afterImageUrl as string }], convertToRGB: "auto" }),
          opacity: 1,
          visible: modeRef.current === "after",
          zIndex: 11,
        });
      map.addLayer(afterRef.current);
      attachFirstTileTracker(afterRef.current.getSource(), "after");
    }

    map.getView().fit(bounds3857, { padding: [60, 60, 60, 60], duration: 0, maxZoom: 15 });
    applyLayerVisibility(modeRef.current, basemapRef.current);
    renderVectorsRef.current();
  }, [aoi, applyLayerVisibility, attachFirstTileTracker]);

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
    renderSignals();
  }, [renderSignals]);

  useEffect(() => {
    applyLayerVisibility(mode, basemapRef.current);
    setDebug(featuresRef.current.filter((feature) => feature.properties.aoi_id === aoi.id && passesFilter(feature, filter, vlm)));
  }, [aoi.id, applyLayerVisibility, filter, mode, setDebug, vlm]);

  useEffect(() => {
    focusFeature(selectedId);
  }, [focusFeature, focusToken, selectedId]);

  useEffect(() => {
    focusSignal(selectedSignalId);
  }, [focusSignal, focusToken, selectedSignalId]);

  return (
    <div
      ref={nodeRef}
      className="map-node"
      role="region"
      aria-label={`Mapa operacional de ${aoi.name.es}`}
      data-filter={filter}
      data-mode={mode}
      data-basemap={basemap}
      data-opacity={opacity}
      data-selected-id={selectedId ?? ""}
      data-selected-signal-id={selectedSignalId ?? ""}
      data-signals-visible={showOperationalSignals ? "true" : "false"}
    />
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

function googleMapsUrl(feature: DamageFeature) {
  const p = feature.properties;
  if (typeof p.google_maps_url === "string" && p.google_maps_url) return p.google_maps_url;
  const point = featureInspectionPoint(feature);
  if (!point) return "";
  return `https://www.google.com/maps/search/?api=1&query=${point.lat},${point.lon}`;
}

function formatSignalValue(value: number | null | undefined) {
  return value === null || value === undefined ? "suppressed" : String(value);
}

function signalPriorityLabel(priority: OperationalSignalFeature["properties"]["priority"]) {
  if (priority === "high") return "High review priority";
  if (priority === "medium") return "Medium review priority";
  return "Context signal";
}

function signalPopupHtml(p: OperationalSignalFeature["properties"]) {
  return (
    `<strong>${escapeHtml(p.id)}</strong>` +
    `<span>${escapeHtml(signalPriorityLabel(p.priority))}</span>` +
    `<span>Community: ${escapeHtml(formatSignalValue(p.communityReports))}</span>` +
    `<span>EMS D/D: ${p.emsOfficialDestroyedDamaged}</span>` +
    `<span>External gap: ${escapeHtml(formatSignalValue(p.externalGapCandidates))}</span>` +
    `<small>Aggregate zone only · triage guidance</small>`
  );
}

function popupHtml(feature: DamageFeature) {
  const p = feature.properties;
  const mapsUrl = googleMapsUrl(feature);
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
