#!/usr/bin/env python3
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


PUBLIC_REPORT_PDF_MAX_BYTES = 5 * 1024 * 1024


def run(args):
    return subprocess.check_output(args, text=True)


def prepare_input(path):
    path = Path(path)
    if path.is_dir():
        return path, None
    if path.suffix.lower() == ".zip":
        tmp = tempfile.TemporaryDirectory()
        with zipfile.ZipFile(path) as zf:
            zf.extractall(tmp.name)
        return Path(tmp.name), tmp
    raise SystemExit(f"Unsupported input: {path}")


def find_product_root(root):
    gpkg = sorted(root.rglob("*_v*.gpkg"))
    if gpkg:
        return gpkg[0].parent
    shp = sorted(root.rglob("*_builtUp[AP]_v*.shp"))
    if shp:
        return shp[0].parent
    raise SystemExit(f"No EMS GeoPackage/Shapefile found under {root}")


def layer_source(product_root):
    gpkg = sorted(product_root.glob("*_v*.gpkg"))
    if gpkg:
        info = run(["ogrinfo", str(gpkg[0])])
        layers = []
        for line in info.splitlines():
            match = re.match(r"\s*\d+:\s+(builtUp[AP]_v(\d+))\b", line)
            if match:
                name, version = match.groups()
                geometry_priority = 0 if name.startswith("builtUpA_") else 1
                layers.append((geometry_priority, -int(version), name))
        if layers:
            _, _, layer = sorted(layers)[0]
            return str(gpkg[0]), layer, gpkg[0]
    shp = sorted(product_root.glob("*_builtUp[AP]_v*.shp"))
    if shp:
        return str(shp[0]), None, shp[0]
    raise SystemExit(f"No builtUpA/builtUpP layer found in {product_root}")


def product_id_from_path(product_path, product_root):
    stem = product_path.stem
    if "_v" in stem:
        return stem.rsplit("_v", 1)[0]
    return product_root.name


def source_product_label(input_path):
    return Path(input_path).name


def convert_to_geojson(src, layer, out_geojson):
    args = [
        "ogr2ogr",
        "-f",
        "GeoJSON",
        "-t_srs",
        "EPSG:4326",
        str(out_geojson),
        src,
    ]
    if layer:
        args.append(layer)
    subprocess.run(args, check=True)


def severity(damage_gra):
    value = (damage_gra or "").strip().lower()
    if value == "destroyed":
        return 100, "destroyed"
    if value == "damaged":
        return 70, "damaged"
    if value == "possibly damaged":
        return 35, "possibly-damaged"
    if value == "no visible damage":
        return 0, "no-visible-damage"
    return 0, "unknown"


def centroid(coords):
    pts = []
    def walk(x):
        if isinstance(x, (list, tuple)) and x and isinstance(x[0], (int, float)):
            pts.append(x)
        elif isinstance(x, (list, tuple)):
            for y in x:
                walk(y)
    walk(coords)
    if not pts:
        return "", ""
    lon = sum(p[0] for p in pts) / len(pts)
    lat = sum(p[1] for p in pts) / len(pts)
    return lat, lon


def build_kml(rows, path):
    colors = {
        "destroyed": "ff00005b",
        "damaged": "ff1a12c4",
        "possibly-damaged": "ff229be4",
        "unknown": "ff888888",
    }
    marks = []
    for row in rows:
        if row["damage_class"] in ("unknown", "no-visible-damage"):
            continue
        desc = "<![CDATA[" + (
            f"<b>AOI:</b> {escape(row['aoi'])}<br/>"
            f"<b>EMS damage:</b> {escape(row['damage_gra'])}<br/>"
            f"<b>Damage %:</b> {escape(str(row['damage_percent']))}<br/>"
            f"<b>Object:</b> {escape(row['obj_type'])}<br/>"
            f"<b>Detection:</b> {escape(row['det_method'])}<br/>"
            f"<b>Google Maps:</b> <a href='{escape(row['google_maps_url'])}'>open</a><br/>"
        ) + "]]>"
        marks.append(f"""
    <Placemark>
      <name>{escape(row['id'])}</name>
      <description>{desc}</description>
      <Style><IconStyle><color>{colors.get(row['damage_class'], 'ff888888')}</color><scale>0.9</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>
      <Point><coordinates>{row['centroid_lon']},{row['centroid_lat']},0</coordinates></Point>
    </Placemark>""")
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>EMS Damage Assessment</name>\n'
        + "\n".join(marks)
        + "\n</Document></kml>\n"
    )


def write_simple_viewer(out, geojson_name, title):
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
html,body,#map{{height:100%;margin:0;font-family:system-ui,-apple-system,Segoe UI,sans-serif}}
.panel{{position:absolute;z-index:500;left:12px;top:12px;width:360px;max-width:calc(100vw - 24px);background:white;border:1px solid #ccc;padding:12px;box-shadow:0 4px 16px #0002}}
.kpis{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:8px 0}}
.kpi{{border:1px solid #ddd;padding:8px}} .kpi b{{font-size:18px;display:block}}
button{{border:1px solid #bbb;background:white;padding:6px 8px;margin:2px;cursor:pointer}} button.active{{background:#111;color:white}}
</style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <h2 style="margin:0 0 6px;font-size:17px">{title}</h2>
  <div>Copernicus EMS-compatible grading layer. This viewer expects official GRA/BLP vector products.</div>
  <div id="kpis" class="kpis"></div>
  <div><button class="active" data-filter="all">All</button><button data-filter="Damaged">Damaged</button><button data-filter="Possibly damaged">Possibly damaged</button></div>
  <p style="font-size:12px;color:#555">Exports: <a href="data/ems_builtup_damage.csv">CSV</a> · <a href="data/ems_builtup_damage.geojson">GeoJSON</a> · <a href="data/ems_builtup_damage.kml">KML</a></p>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const map=L.map('map').setView([10.48,-67],12);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:20,attribution:'&copy; OpenStreetMap'}}).addTo(map);
let data, layer, filter='all';
const color=p=>p.damage_gra==='Damaged'?'#c4121a':p.damage_gra==='Possibly damaged'?'#e49b22':'#777';
function popup(p){{return `<b>${{p.id}}</b><br>EMS: <b>${{p.damage_gra}}</b><br>Object: ${{p.obj_type||''}}<br>Detection: ${{p.det_method||''}}<br><a target="_blank" href="${{p.google_maps_url}}">Google Maps</a>`}}
function render(){{if(layer) layer.remove(); const feats=data.features.filter(f=>filter==='all'||f.properties.damage_gra===filter); layer=L.geoJSON({{type:'FeatureCollection',features:feats}},{{style:f=>({{color:color(f.properties),fillColor:color(f.properties),fillOpacity:.35,weight:2}}),onEachFeature:(f,l)=>l.bindPopup(popup(f.properties))}}).addTo(map); if(feats.length) map.fitBounds(layer.getBounds(),{{padding:[24,24]}}); document.getElementById('kpis').innerHTML=`<div class="kpi"><b>${{data.features.length}}</b><span>total</span></div><div class="kpi"><b>${{data.features.filter(f=>f.properties.damage_gra==='Damaged').length}}</b><span>damaged</span></div><div class="kpi"><b>${{data.features.filter(f=>f.properties.damage_gra==='Possibly damaged').length}}</b><span>possible</span></div>`}}
fetch('data/{geojson_name}').then(r=>r.json()).then(j=>{{data=j; render();}});
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('button').forEach(x=>x.classList.remove('active')); b.classList.add('active'); filter=b.dataset.filter; render();}});
</script>
</body>
</html>
"""
    (out / "index.html").write_text(html)


def main():
    if len(sys.argv) < 3:
        raise SystemExit("Usage: build_copernicus_ems_package.py EMS_PRODUCT_ZIP_OR_DIR OUT_DIR")
    input_path = Path(sys.argv[1])
    out = Path(sys.argv[2])
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    (out / "metadata").mkdir()
    (out / "reports").mkdir()

    root, tmp = prepare_input(input_path)
    try:
        product_root = find_product_root(root)
        src, layer, product_path = layer_source(product_root)
        product_id = product_id_from_path(Path(product_path), product_root)
        raw_geojson = out / "data" / "ems_builtup_damage.geojson"
        convert_to_geojson(src, layer, raw_geojson)
        geo = json.loads(raw_geojson.read_text())
        rows = []
        for i, feat in enumerate(geo["features"], start=1):
            p = feat.setdefault("properties", {})
            lat, lon = centroid(feat["geometry"]["coordinates"])
            pct, cls = severity(p.get("damage_gra"))
            row = {
                "id": f"ems_{i:05d}",
                "aoi": product_id,
                "obj_type": p.get("obj_type", ""),
                "name": p.get("name", ""),
                "info": p.get("info", ""),
                "simplified": p.get("simplified", ""),
                "damage_gra": p.get("damage_gra", ""),
                "damage_class": cls,
                "damage_percent": pct,
                "det_method": p.get("det_method", ""),
                "notation": p.get("notation", ""),
                "or_src_id": p.get("or_src_id", ""),
                "dmg_src_id": p.get("dmg_src_id", ""),
                "centroid_lat": lat,
                "centroid_lon": lon,
                "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
            }
            p.update(row)
            rows.append(row)

        raw_geojson.write_text(json.dumps(geo, ensure_ascii=True))
        with (out / "data" / "ems_builtup_damage.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["id"])
            writer.writeheader()
            writer.writerows(rows)
        build_kml(rows, out / "data" / "ems_builtup_damage.kml")

        pdfs = list(product_root.rglob("*.pdf"))
        skipped_pdf = None
        if pdfs:
            if pdfs[0].stat().st_size <= PUBLIC_REPORT_PDF_MAX_BYTES:
                shutil.copy2(pdfs[0], out / "reports" / pdfs[0].name)
            else:
                skipped_pdf = pdfs[0].name
        xlsx = list(product_root.rglob("*summaryTable*.xlsx"))
        if xlsx:
            shutil.copy2(xlsx[0], out / "reports" / xlsx[0].name)

        counts = {
            "features": len(rows),
            "destroyed": sum(r["damage_gra"] == "Destroyed" for r in rows),
            "damaged": sum(r["damage_gra"] == "Damaged" for r in rows),
            "possibly_damaged": sum(r["damage_gra"] == "Possibly damaged" for r in rows),
            "source_product": source_product_label(input_path),
            "source_root": product_id,
            "source_file": Path(src).name,
            "source_layer": layer or Path(src).name,
        }
        (out / "metadata" / "source_metadata.json").write_text(json.dumps(counts, indent=2))
        (out / "reports" / "README_EMS_COMPATIBILITY.md").write_text(
            "# EMS-Compatible Package\n\n"
            "This package is generated directly from Copernicus EMS GRA/BLP vectors.\n\n"
            f"- Input layer: `{layer or Path(src).name}`\n"
            "- Key EMS field: `damage_gra`\n"
            "- Outputs: CSV, GeoJSON, KML, static map viewer\n\n"
            + (f"- Map PDF `{skipped_pdf}` was not copied because it exceeds the 5 MB public package budget; keep the source EMS ZIP as the full official report source.\n\n" if skipped_pdf else "")
            + "For AOI12 La Guaira, run this same builder on the AOI12 GRA zip when it becomes downloadable.\n"
        )
        write_simple_viewer(out, "ems_builtup_damage.geojson", f"EMS Damage Layer - {product_id}")
        print(out)
        print(json.dumps(counts, indent=2))
    finally:
        if tmp:
            tmp.cleanup()


if __name__ == "__main__":
    main()
