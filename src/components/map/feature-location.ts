import type { DamageFeature } from "../types";

type LonLat = { lon: number; lat: number };
type Position = [number, number, ...number[]];

function finiteLonLat(lon: number, lat: number): LonLat | null {
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return null;
  if (lon < -180 || lon > 180 || lat < -90 || lat > 90) return null;
  return { lon, lat };
}

function featureCentroid(feature: DamageFeature) {
  const lat = Number(feature.properties.centroid_lat);
  const lon = Number(feature.properties.centroid_lon);
  return finiteLonLat(lon, lat);
}

function positionLonLat(position: unknown): LonLat | null {
  if (!Array.isArray(position) || position.length < 2) return null;
  return finiteLonLat(Number(position[0]), Number(position[1]));
}

function onSegment(point: LonLat, a: Position, b: Position) {
  const cross = (point.lat - a[1]) * (b[0] - a[0]) - (point.lon - a[0]) * (b[1] - a[1]);
  if (Math.abs(cross) > 1e-10) return false;
  const dot = (point.lon - a[0]) * (b[0] - a[0]) + (point.lat - a[1]) * (b[1] - a[1]);
  if (dot < 0) return false;
  const squaredLength = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2;
  return dot <= squaredLength;
}

function pointInRing(point: LonLat, ring: Position[]) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const a = ring[i];
    const b = ring[j];
    if (!a || !b) continue;
    if (onSegment(point, a, b)) return true;
    const crosses = (a[1] > point.lat) !== (b[1] > point.lat);
    if (crosses) {
      const lonAtLat = ((b[0] - a[0]) * (point.lat - a[1])) / (b[1] - a[1]) + a[0];
      if (point.lon < lonAtLat) inside = !inside;
    }
  }
  return inside;
}

function pointInPolygon(point: LonLat, polygon: Position[][]) {
  const outer = polygon[0];
  if (!outer || !pointInRing(point, outer)) return false;
  return polygon.slice(1).every((hole) => !pointInRing(point, hole));
}

function pointInGeometry(point: LonLat, geometry: GeoJSON.Geometry | null | undefined): boolean {
  if (!geometry) return true;
  if (geometry.type === "Polygon") return pointInPolygon(point, geometry.coordinates as Position[][]);
  if (geometry.type === "MultiPolygon") {
    return (geometry.coordinates as Position[][][]).some((polygon) => pointInPolygon(point, polygon));
  }
  return true;
}

function ringArea(ring: Position[]) {
  let area = 0;
  for (let i = 0; i < ring.length - 1; i += 1) {
    const a = ring[i];
    const b = ring[i + 1];
    if (!a || !b) continue;
    area += a[0] * b[1] - b[0] * a[1];
  }
  return area / 2;
}

function ringCentroid(ring: Position[]): LonLat | null {
  let twiceArea = 0;
  let lon = 0;
  let lat = 0;
  for (let i = 0; i < ring.length - 1; i += 1) {
    const a = ring[i];
    const b = ring[i + 1];
    if (!a || !b) continue;
    const cross = a[0] * b[1] - b[0] * a[1];
    twiceArea += cross;
    lon += (a[0] + b[0]) * cross;
    lat += (a[1] + b[1]) * cross;
  }
  if (Math.abs(twiceArea) < 1e-12) return positionLonLat(ring[0]);
  return finiteLonLat(lon / (3 * twiceArea), lat / (3 * twiceArea));
}

function ringBoundsCenter(ring: Position[]): LonLat | null {
  let minLon = Infinity;
  let minLat = Infinity;
  let maxLon = -Infinity;
  let maxLat = -Infinity;
  for (const position of ring) {
    const point = positionLonLat(position);
    if (!point) continue;
    minLon = Math.min(minLon, point.lon);
    minLat = Math.min(minLat, point.lat);
    maxLon = Math.max(maxLon, point.lon);
    maxLat = Math.max(maxLat, point.lat);
  }
  if (!Number.isFinite(minLon) || !Number.isFinite(minLat) || !Number.isFinite(maxLon) || !Number.isFinite(maxLat)) return null;
  return finiteLonLat((minLon + maxLon) / 2, (minLat + maxLat) / 2);
}

function polygonRepresentativePoint(polygon: Position[][]): LonLat | null {
  const outer = polygon[0];
  if (!outer) return null;
  const centroid = ringCentroid(outer);
  if (centroid && pointInPolygon(centroid, polygon)) return centroid;
  const boundsCenter = ringBoundsCenter(outer);
  if (boundsCenter && pointInPolygon(boundsCenter, polygon)) return boundsCenter;
  return positionLonLat(outer[0]);
}

function geometryRepresentativePoint(geometry: GeoJSON.Geometry | null | undefined): LonLat | null {
  if (!geometry) return null;
  if (geometry.type === "Point") return positionLonLat(geometry.coordinates);
  if (geometry.type === "MultiPoint" || geometry.type === "LineString") {
    return positionLonLat(geometry.coordinates[0]);
  }
  if (geometry.type === "MultiLineString") {
    return positionLonLat(geometry.coordinates[0]?.[0]);
  }
  if (geometry.type === "Polygon") return polygonRepresentativePoint(geometry.coordinates as Position[][]);
  if (geometry.type === "MultiPolygon") {
    const polygons = geometry.coordinates as Position[][][];
    const largest = polygons
      .filter((polygon) => polygon[0])
      .sort((a, b) => Math.abs(ringArea(b[0])) - Math.abs(ringArea(a[0])))[0];
    return largest ? polygonRepresentativePoint(largest) : null;
  }
  if (geometry.type === "GeometryCollection") {
    for (const child of geometry.geometries) {
      const point = geometryRepresentativePoint(child);
      if (point) return point;
    }
  }
  return null;
}

export function featureInspectionPoint(feature: DamageFeature): LonLat | null {
  const centroid = featureCentroid(feature);
  if (centroid && pointInGeometry(centroid, feature.geometry)) return centroid;
  return geometryRepresentativePoint(feature.geometry) ?? centroid;
}
