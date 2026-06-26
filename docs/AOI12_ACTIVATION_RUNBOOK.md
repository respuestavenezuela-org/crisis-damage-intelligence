# AOI12 Activation Runbook

Use this when Copernicus publishes the AOI12 Caraballeda/La Guaira GRA ZIP.

## 1. Put The ZIP Here

Recommended local path:

```text
data/incoming/EMSR884_AOI12_Caraballeda_GRA_v1.zip
```

Create the folder if needed:

```bash
mkdir -p data/incoming
```

## 2. Ingest

From the package root:

```bash
bash scripts/emsr884-aoi12-ingest.sh \
  data/incoming/EMSR884_AOI12_Caraballeda_GRA_v1.zip \
  public/data/aoi/emsr884-aoi12-caraballeda
```

This runs:

```bash
python3 scripts/build_copernicus_ems_package.py <AOI12_ZIP> public/data/aoi/emsr884-aoi12-caraballeda
```

The script also copies importer outputs into app-facing paths:

```text
damage.csv
damage.geojson
damage.kml
source_metadata.json
```

## 3. Expected Files

The importer should create:

```text
public/data/aoi/emsr884-aoi12-caraballeda/data/ems_builtup_damage.csv
public/data/aoi/emsr884-aoi12-caraballeda/data/ems_builtup_damage.geojson
public/data/aoi/emsr884-aoi12-caraballeda/data/ems_builtup_damage.kml
public/data/aoi/emsr884-aoi12-caraballeda/metadata/source_metadata.json
public/data/aoi/emsr884-aoi12-caraballeda/reports/*.xlsx
public/data/aoi/emsr884-aoi12-caraballeda/reports/*.pdf
```

For app compatibility, confirm these final public paths exist:

```text
public/data/aoi/emsr884-aoi12-caraballeda/damage.csv
public/data/aoi/emsr884-aoi12-caraballeda/damage.geojson
public/data/aoi/emsr884-aoi12-caraballeda/damage.kml
public/data/aoi/emsr884-aoi12-caraballeda/source_metadata.json
```

## 4. Catalog Entry

Add an AOI entry to `public/data/catalog.json`:

```json
{
  "id": "emsr884-aoi12-caraballeda",
  "country": "Venezuela",
  "event": "EMSR884 Venezuela earthquake",
  "name": {
    "en": "AOI12 Caraballeda / La Guaira - Official EMSR884 Vector",
    "es": "AOI12 Caraballeda / La Guaira - Vector oficial EMSR884"
  },
  "status": "official-vector",
  "source": "Copernicus EMSR884 GRA ZIP -> AOI12 PRODUCT GPKG / builtUpA layer",
  "bounds": [[MIN_LAT, MIN_LON], [MAX_LAT, MAX_LON]],
  "center": [CENTER_LAT, CENTER_LON],
  "downloads": {
    "csv": "/data/aoi/emsr884-aoi12-caraballeda/damage.csv",
    "geojson": "/data/aoi/emsr884-aoi12-caraballeda/damage.geojson",
    "kml": "/data/aoi/emsr884-aoi12-caraballeda/damage.kml"
  },
  "layers": {
    "damage": "/data/aoi/emsr884-aoi12-caraballeda/damage.geojson"
  },
  "metrics": {
    "features": FEATURE_COUNT,
    "destroyed": DESTROYED_COUNT,
    "damagedConfirmed": DESTROYED_PLUS_DAMAGED_COUNT,
    "possibleDamage": POSSIBLY_DAMAGED_COUNT,
    "vlmReviewed": 0
  }
}
```

Remove or update the AOI12 watchlist item after adding the operational AOI.

## 5. QA Checks

Run:

```bash
npm run lint
npm run build
```

Browser checks:

- AOI12 appears in AOI selector.
- AOI12 loads without console errors.
- Map count equals GeoJSON feature count.
- CSV rows, GeoJSON features, and KML placemarks match.
- `Destroyed/Damaged` filter equals `Destroyed + Damaged` from `damage_gra`.
- `Possibly damaged` is not counted as destroyed/damaged.
- First priority click centers at zoom 18.
- Popup has Google Maps link.
- Summary table/PDF counts match generated metadata where possible.

## 6. Publish

For Vercel:

```bash
npm ci
npm run build
vercel --prod
```

For GitHub Actions, use the manual workflow:

```text
Actions -> Manual EMSR884 AOI Ingest
```

Inputs:

```text
aoi_id: emsr884-aoi12-caraballeda
zip_url: <real AOI12 GRA ZIP URL>
output_prefix: public/data/aoi/emsr884-aoi12-caraballeda
```

If object storage secrets are configured, the workflow also uploads:

```text
ems/original-zips/emsr884-aoi12-caraballeda/
ems/generated/emsr884-aoi12-caraballeda/
```

If not using Vercel yet, regenerate the handoff ZIP:

```bash
cd ..
zip -qr crisis_damage_intelligence_platform.zip crisis_damage_intelligence_platform \
  -x 'crisis_damage_intelligence_platform/node_modules/*' \
  -x 'crisis_damage_intelligence_platform/.next/*'
```

## Do Not Overclaim

- EMS `builtUpA` features may not be one building each.
- Official EMS labels are the source of record for this package.
- VLM/inferred labels are triage aids only.
- Absence of a marked feature is not proof of no damage.
