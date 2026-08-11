"use client";

import { useEffect, useRef } from "react";
import Feature from "ol/Feature.js";
import WKT from "ol/format/WKT.js";
import type Geometry from "ol/geom/Geometry.js";
import Point from "ol/geom/Point.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import OlMap from "ol/Map.js";
import { fromLonLat, toLonLat } from "ol/proj.js";
import OSM from "ol/source/OSM.js";
import VectorSource from "ol/source/Vector.js";
import XYZ from "ol/source/XYZ.js";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style.js";
import View from "ol/View.js";
import { defaults as defaultControls } from "ol/control/defaults.js";
import "ol/ol.css";
import type {
  ColombiaLanguage,
  ColombiaMapMode,
  ColombiaMappingSnapshot,
} from "./types";
import styles from "../../app/colombia/colombia.module.css";

declare global {
  interface Window {
    __colombiaMapDebug?: {
      mode: ColombiaMapMode;
      selectedAoiId: string | null;
      visibleAoiIds: string[];
      center: { longitude: number; latitude: number };
      zoom: number | undefined;
      beforeReady: boolean;
      afterReady: boolean;
    };
  }
}

type AoiFeature = Feature<Geometry>;

function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function fitPadding() {
  return window.matchMedia("(max-width: 760px)").matches
    ? [72, 32, Math.min(window.innerHeight * 0.48, 390), 32]
    : [72, 56, 72, 404];
}

function aoiStyle(feature: AoiFeature, selectedAoiId: string | null) {
  const selected = feature.get("aoiId") === selectedAoiId;
  const productType = String(feature.get("productType") ?? "");
  const color = productType === "GRA" ? "#f0a329" : "#2c9c84";

  return new Style({
    fill: new Fill({
      color: selected
        ? productType === "GRA"
          ? "rgba(240, 163, 41, 0.28)"
          : "rgba(44, 156, 132, 0.22)"
        : productType === "GRA"
          ? "rgba(240, 163, 41, 0.10)"
          : "rgba(44, 156, 132, 0.08)",
    }),
    stroke: new Stroke({
      color: selected ? "#fffdf8" : color,
      width: selected ? 4 : productType === "GRA" ? 2.5 : 2,
      lineDash: productType === "GRA" ? undefined : [8, 5],
    }),
    zIndex: selected ? 20 : productType === "GRA" ? 12 : 10,
  });
}

function imageryLayer(
  descriptor: ColombiaMappingSnapshot["imagery"]["before"],
  visible: boolean,
) {
  if (!descriptor) return null;
  return new TileLayer({
    visible,
    source: new XYZ({
      url: descriptor.urlTemplate,
      minZoom: descriptor.minZoom,
      maxZoom: descriptor.maxZoom,
      attributions: descriptor.attribution,
      crossOrigin: "anonymous",
    }),
  });
}

export default function ColombiaMapCanvas({
  mapping,
  mode,
  language,
  selectedAoiId,
  epicenter,
  onSelectAoi,
}: {
  mapping: ColombiaMappingSnapshot;
  mode: ColombiaMapMode;
  language: ColombiaLanguage;
  selectedAoiId: string | null;
  epicenter: { longitude: number; latitude: number };
  onSelectAoi: (aoiId: string) => void;
}) {
  const nodeRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<OlMap | null>(null);
  const aoiSourceRef = useRef<VectorSource<AoiFeature> | null>(null);
  const mapLayerRef = useRef<TileLayer<OSM> | null>(null);
  const referenceLayerRef = useRef<TileLayer<XYZ> | null>(null);
  const beforeLayerRef = useRef<TileLayer<XYZ> | null>(null);
  const afterLayerRef = useRef<TileLayer<XYZ> | null>(null);
  const selectedRef = useRef<string | null>(selectedAoiId);
  const onSelectRef = useRef(onSelectAoi);
  const initialModeRef = useRef(mode);
  const modeRef = useRef(mode);

  useEffect(() => {
    selectedRef.current = selectedAoiId;
    aoiSourceRef.current?.changed();
  }, [selectedAoiId]);

  useEffect(() => {
    onSelectRef.current = onSelectAoi;
  }, [onSelectAoi]);

  useEffect(() => {
    if (!nodeRef.current || mapRef.current) return;

    const format = new WKT();
    const aoiFeatures = mapping.aois.map((aoi) => {
      const feature = format.readFeature(aoi.extentWkt, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      }) as AoiFeature;
      feature.setProperties({
        aoiId: aoi.id,
        aoiNumber: aoi.number,
        productType: aoi.products[0]?.type ?? "",
      });
      return feature;
    });
    const aoiSource = new VectorSource<AoiFeature>({ features: aoiFeatures });
    const aoiLayer = new VectorLayer({
      source: aoiSource,
      style: (feature) => aoiStyle(feature as AoiFeature, selectedRef.current),
      zIndex: 20,
    });

    const epicenterFeature = new Feature({
      geometry: new Point(fromLonLat([epicenter.longitude, epicenter.latitude])),
    });
    const epicenterLayer = new VectorLayer({
      source: new VectorSource({ features: [epicenterFeature] }),
      style: new Style({
        image: new CircleStyle({
          radius: 9,
          fill: new Fill({ color: "#d94a32" }),
          stroke: new Stroke({ color: "#fffdf8", width: 4 }),
        }),
      }),
      zIndex: 30,
    });

    const mapLayer = new TileLayer({
      visible: initialModeRef.current === "map",
      source: new OSM({ crossOrigin: "anonymous" }),
      zIndex: 0,
    });
    const referenceLayer = new TileLayer({
      visible: initialModeRef.current === "reference",
      source: new XYZ({
        url: mapping.imagery.reference.urlTemplate,
        minZoom: mapping.imagery.reference.minZoom,
        maxZoom: mapping.imagery.reference.maxZoom,
        attributions: mapping.imagery.reference.attribution,
        crossOrigin: "anonymous",
      }),
      zIndex: 1,
    });
    const beforeLayer = imageryLayer(
      mapping.imagery.before,
      initialModeRef.current === "before",
    );
    const afterLayer = imageryLayer(
      mapping.imagery.after,
      initialModeRef.current === "after",
    );

    const layers = [
      mapLayer,
      referenceLayer,
      ...(beforeLayer ? [beforeLayer] : []),
      ...(afterLayer ? [afterLayer] : []),
      aoiLayer,
      epicenterLayer,
    ];
    const map = new OlMap({
      target: nodeRef.current,
      controls: defaultControls({
        rotate: false,
        zoom: true,
        attribution: true,
      }),
      layers,
      view: new View({
        center: fromLonLat([-76.34, 4.15]),
        zoom: 7,
        minZoom: 5,
        maxZoom: 18,
      }),
    });

    const updateDebug = () => {
      const center = toLonLat(map.getView().getCenter() ?? [0, 0]);
      window.__colombiaMapDebug = {
        mode: modeRef.current,
        selectedAoiId: selectedRef.current,
        visibleAoiIds: mapping.aois.map((aoi) => aoi.id),
        center: { longitude: center[0], latitude: center[1] },
        zoom: map.getView().getZoom(),
        beforeReady: Boolean(mapping.imagery.before),
        afterReady: Boolean(mapping.imagery.after),
      };
    };

    const fitActivation = () => {
      const extentFeature = format.readFeature(mapping.extentWkt, {
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:3857",
      });
      const extent = extentFeature.getGeometry()?.getExtent();
      if (!extent) return;
      map.getView().fit(extent, {
        padding: fitPadding(),
        maxZoom: 8,
        duration: 0,
      });
      updateDebug();
    };

    map.once("rendercomplete", fitActivation);
    map.on("moveend", updateDebug);
    map.on("singleclick", (event) => {
      const feature = map.forEachFeatureAtPixel(
        event.pixel,
        (candidate) => candidate as AoiFeature,
        {
          hitTolerance: 7,
          layerFilter: (layer) => layer === aoiLayer,
        },
      );
      const aoiId = feature?.get("aoiId");
      if (typeof aoiId === "string") onSelectRef.current(aoiId);
    });
    map.on("pointermove", (event) => {
      const target = map.getTargetElement();
      const overAoi = map.hasFeatureAtPixel(event.pixel, {
        hitTolerance: 5,
        layerFilter: (layer) => layer === aoiLayer,
      });
      target.style.cursor = overAoi ? "pointer" : "";
    });

    const resizeObserver = new ResizeObserver(() => map.updateSize());
    resizeObserver.observe(nodeRef.current);

    mapRef.current = map;
    aoiSourceRef.current = aoiSource;
    mapLayerRef.current = mapLayer;
    referenceLayerRef.current = referenceLayer;
    beforeLayerRef.current = beforeLayer;
    afterLayerRef.current = afterLayer;
    updateDebug();

    return () => {
      resizeObserver.disconnect();
      map.setTarget(undefined);
      mapRef.current = null;
      aoiSourceRef.current = null;
      mapLayerRef.current = null;
      referenceLayerRef.current = null;
      beforeLayerRef.current = null;
      afterLayerRef.current = null;
      delete window.__colombiaMapDebug;
    };
  }, [epicenter.latitude, epicenter.longitude, mapping]);

  useEffect(() => {
    modeRef.current = mode;
    mapLayerRef.current?.setVisible(mode === "map");
    referenceLayerRef.current?.setVisible(mode === "reference");
    beforeLayerRef.current?.setVisible(mode === "before");
    afterLayerRef.current?.setVisible(mode === "after");
    mapRef.current?.render();
    if (window.__colombiaMapDebug) window.__colombiaMapDebug.mode = mode;
  }, [mode]);

  useEffect(() => {
    const map = mapRef.current;
    const source = aoiSourceRef.current;
    if (!map || !source || !selectedAoiId) return;
    const feature = source
      .getFeatures()
      .find((candidate) => candidate.get("aoiId") === selectedAoiId);
    const extent = feature?.getGeometry()?.getExtent();
    if (!extent) return;
    map.getView().fit(extent, {
      padding: fitPadding(),
      maxZoom: feature?.get("productType") === "GRA" ? 15 : 8.5,
      duration: prefersReducedMotion() ? 0 : 360,
    });
    if (window.__colombiaMapDebug) {
      window.__colombiaMapDebug.selectedAoiId = selectedAoiId;
    }
  }, [selectedAoiId]);

  const mapLabel =
    language === "es"
      ? "Mapa interactivo del sismo de Colombia con cuatro áreas oficiales de cartografía Copernicus EMSR916"
      : "Interactive Colombia earthquake map with four official Copernicus EMSR916 mapping areas";

  return (
    <div
      ref={nodeRef}
      id="mapa-colombia"
      className={styles.mapCanvas}
      data-testid="colombia-map-canvas"
      data-mode={mode}
      data-selected-aoi={selectedAoiId ?? ""}
      data-visible-aoi-count={mapping.aois.length}
      data-before-ready={String(Boolean(mapping.imagery.before))}
      data-after-ready={String(Boolean(mapping.imagery.after))}
      role="region"
      aria-label={mapLabel}
      tabIndex={0}
    />
  );
}
