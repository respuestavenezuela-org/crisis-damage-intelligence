"use client";

import { useEffect, useRef } from "react";
import Feature from "ol/Feature.js";
import OlMap from "ol/Map.js";
import View from "ol/View.js";
import { defaults as defaultControls } from "ol/control/defaults.js";
import { boundingExtent } from "ol/extent.js";
import Point from "ol/geom/Point.js";
import VectorLayer from "ol/layer/Vector.js";
import TileLayer from "ol/layer/Tile.js";
import { fromLonLat } from "ol/proj.js";
import OSM from "ol/source/OSM.js";
import VectorSource from "ol/source/Vector.js";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style.js";
import "ol/ol.css";
import type { EvidenceLanguage, EvidenceObservation } from "./types";
import styles from "./evidence-explorer.module.css";

const categoryColors: Record<string, string> = {
  heavy_machinery: "#e1a52a",
  trucks_or_large_vehicles: "#c85836",
  temporary_shelter: "#2e7b68",
  collection_or_staging: "#4769a8",
  debris_clearance: "#7c6655",
  emergency_or_service_vehicle: "#b84562",
};

function markerColor(observation: EvidenceObservation) {
  for (const category of Object.keys(categoryColors)) {
    if (observation.assetCategories.includes(category)) {
      return categoryColors[category];
    }
  }
  return "#656b64";
}

type EvidenceMapFeature = Feature<Point>;

export default function EvidenceMap({
  observations,
  filtered,
  selectedCellId,
  onSelect,
  label,
  language,
}: {
  observations: EvidenceObservation[];
  filtered: EvidenceObservation[];
  selectedCellId: string | null;
  onSelect: (cellId: string) => void;
  label: string;
  language: EvidenceLanguage;
}) {
  const nodeRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<OlMap | null>(null);
  const sourceRef = useRef<VectorSource<EvidenceMapFeature> | null>(null);
  const selectedRef = useRef<string | null>(selectedCellId);
  const onSelectRef = useRef(onSelect);
  const fittedRef = useRef(false);

  useEffect(() => {
    selectedRef.current = selectedCellId;
  }, [selectedCellId]);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    if (!nodeRef.current || mapRef.current) return;
    const source = new VectorSource<EvidenceMapFeature>();
    const styleCache = new Map<string, Style>();
    const markerLayer = new VectorLayer({
      source,
      zIndex: 10,
      style: (feature) => {
        const active = Boolean(feature.get("active"));
        const selected = feature.get("cellId") === selectedRef.current;
        const color = String(feature.get("color") ?? "#656b64");
        const key = `${color}-${active ? "active" : "muted"}-${selected ? "selected" : "normal"}`;
        const cached = styleCache.get(key);
        if (cached) return cached;
        const style = new Style({
          image: new CircleStyle({
            radius: selected ? 8 : active ? 5 : 3,
            fill: new Fill({
              color: active ? color : "rgba(51, 65, 57, 0.2)",
            }),
            stroke: new Stroke({
              color: selected ? "#111610" : active ? "#fffdf7" : "rgba(255,255,255,0.45)",
              width: selected ? 3 : 1.25,
            }),
          }),
        });
        styleCache.set(key, style);
        return style;
      },
    });
    const map = new OlMap({
      target: nodeRef.current,
      controls: defaultControls({ rotate: false, zoom: true, attribution: true }),
      layers: [
        new TileLayer({
          source: new OSM({ crossOrigin: "anonymous" }),
          zIndex: 0,
        }),
        markerLayer,
      ],
      view: new View({
        center: fromLonLat([-66.94, 10.6]),
        zoom: 11.2,
        minZoom: 9,
        maxZoom: 18,
      }),
    });

    map.on("singleclick", (event) => {
      const feature = map.forEachFeatureAtPixel(
        event.pixel,
        (candidate) => candidate as EvidenceMapFeature,
        { hitTolerance: 8 },
      );
      const cellId = feature?.get("cellId");
      if (typeof cellId === "string") onSelectRef.current(cellId);
    });
    map.on("pointermove", (event) => {
      const target = map.getTargetElement();
      target.style.cursor = map.hasFeatureAtPixel(event.pixel, { hitTolerance: 6 })
        ? "pointer"
        : "";
    });

    sourceRef.current = source;
    mapRef.current = map;
    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
      sourceRef.current = null;
    };
  }, []);

  useEffect(() => {
    const source = sourceRef.current;
    const map = mapRef.current;
    if (!source || !map) return;
    const filteredIds = new Set(filtered.map((item) => item.cellId));
    const features = observations.map((observation) => {
      const feature = new Feature({
        geometry: new Point(fromLonLat([observation.longitude, observation.latitude])),
      }) as EvidenceMapFeature;
      feature.setProperties({
        cellId: observation.cellId,
        active: filteredIds.has(observation.cellId),
        color: markerColor(observation),
      });
      return feature;
    });
    source.clear(true);
    source.addFeatures(features);
    source.changed();

    if (!fittedRef.current && features.length) {
      const coordinates = features
        .map((feature) => feature.getGeometry()?.getCoordinates())
        .filter((coordinate): coordinate is number[] => Boolean(coordinate));
      map.getView().fit(boundingExtent(coordinates), {
        padding: [42, 42, 42, 42],
        maxZoom: 13,
        duration: 0,
      });
      fittedRef.current = true;
    }
  }, [observations, filtered]);

  useEffect(() => {
    const source = sourceRef.current;
    const map = mapRef.current;
    if (!source || !map) return;
    source.changed();
    if (!selectedCellId) return;
    const feature = source
      .getFeatures()
      .find((candidate) => candidate.get("cellId") === selectedCellId);
    const coordinate = feature?.getGeometry()?.getCoordinates();
    if (coordinate) {
      map.getView().animate({
        center: coordinate,
        zoom: Math.max(map.getView().getZoom() ?? 12, 14),
        duration: 240,
      });
    }
  }, [selectedCellId]);

  return (
    <div className={styles.mapFrame}>
      <div className={styles.mapHeading}>
        <div>
          <span>OpenStreetMap · WGS84 · 250 m</span>
          <b>{label}</b>
        </div>
        <strong>{filtered.length}</strong>
      </div>
      <div
        ref={nodeRef}
        className={styles.contextMap}
        role="img"
        aria-label={label}
      />
      <p className={styles.mapFallback}>
        {language === "es"
          ? "El mapa aporta calles y lugares como contexto. La lista conserva acceso a todas las candidatas si las teselas externas no cargan."
          : "The map adds streets and places as context. The list preserves access to every candidate if external tiles fail."}
      </p>
      <div className={styles.mapLegend} aria-hidden="true">
        <span>
          <i style={{ background: categoryColors.heavy_machinery }} />
          {language === "es" ? "Maquinaria" : "Machinery"}
        </span>
        <span>
          <i style={{ background: categoryColors.trucks_or_large_vehicles }} />
          {language === "es" ? "Vehículos" : "Vehicles"}
        </span>
        <span>
          <i style={{ background: categoryColors.temporary_shelter }} />
          {language === "es" ? "Refugio" : "Shelter"}
        </span>
        <span>
          <i style={{ background: categoryColors.collection_or_staging }} />
          {language === "es" ? "Acopio" : "Staging"}
        </span>
      </div>
    </div>
  );
}
