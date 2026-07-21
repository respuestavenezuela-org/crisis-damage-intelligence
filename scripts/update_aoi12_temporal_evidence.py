#!/usr/bin/env python3
"""Publish the human-reviewed AOI12 temporal imagery findings."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "public" / "data" / "reconstruction" / "aerial-response-evidence-la-guaira.json"
TIMELINE_PATH = ROOT / "public" / "data" / "reconstruction" / "la-guaira-timeline.json"
CATALOG_PATH = ROOT / "public" / "data" / "reconstruction" / "catalog.json"
INVENTORY_PATH = ROOT / "public" / "data" / "imagery" / "emsr884-acquisitions.json"
VANTOR_MANIFEST_PATH = ROOT / "ops" / "data_acquisition_plan" / "aoi12_vantor_temporal_review" / "manifest.json"
TEMPORAL_PUBLIC_DIR = ROOT / "public" / "data" / "reconstruction" / "evidence" / "la-guaira" / "temporal"
UPDATED_AT = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


FINDINGS: dict[str, dict[str, Any]] = {
    "ems_00031": {
        "reviewStatus": "weakens-response-attribution",
        "finding": {
            "es": "La imagen del 27 de junio muestra varios vehículos, remolques o contenedores largos y de colores vivos en el mismo patio industrial. La persistencia y el contexto debilitan la atribución de la forma roja del 26 de junio a la respuesta sísmica; el tipo exacto de objeto sigue sin resolverse.",
            "en": "The June 27 image shows several long, brightly coloured vehicles, trailers or containers in the same industrial yard. Persistence and yard context weaken attribution of the June 26 red form to the earthquake response; exact object type remains unresolved.",
        },
        "limitations": {
            "es": "Sensores, geometría y sombras distintos. La persistencia no demuestra función, propiedad ni movimiento.",
            "en": "Different sensors, geometry and shadows. Persistence does not establish function, ownership or movement.",
        },
    },
    "ems_00056": {
        "reviewStatus": "weakens-response-attribution",
        "finding": {
            "es": "La vista más limpia del 27 de junio muestra un patio con vehículos u objetos pequeños alrededor de edificios preexistentes de techo rojo. No se identifica un centro de acopio organizado ni un área de pernocta. Esto debilita la interpretación de uso de respuesta, pero no demuestra que esos usos no existieran en otro lugar o momento.",
            "en": "The cleaner June 27 view shows a yard with small vehicles or objects around pre-existing red-roofed buildings. No organised collection centre or sleeping area is identifiable. This weakens the response-site interpretation but does not show those uses were absent elsewhere or at another time.",
        },
        "limitations": {
            "es": "Una escena puntual no mide actividad, ocupación ni uso fuera de la hora de adquisición.",
            "en": "A single scene does not measure activity, occupancy or use outside its acquisition time.",
        },
    },
    "ems_00108": {
        "reviewStatus": "supports-object-persistence",
        "finding": {
            "es": "La vista del 29 de junio todavía muestra un objeto amarillo de escala de maquinaria junto a un objeto rojo alargado en el mismo sitio de apariencia industrial. La persistencia respalda la presencia de equipo o maquinaria, pero no cuándo llegó ni si tenía una función de emergencia.",
            "en": "The June 29 view still shows a yellow equipment-scale object beside a long red object at the same industrial-looking site. Persistence supports the presence of equipment or machinery, but not when it arrived or whether it served an emergency function.",
        },
        "limitations": {
            "es": "La resolución no establece operador, propiedad, actividad ni relación causal con el sismo.",
            "en": "Resolution does not establish operator, ownership, activity or a causal relationship to the earthquake.",
        },
    },
    "ems_00117": {
        "reviewStatus": "supports-object-persistence",
        "finding": {
            "es": "La escena del 29 de junio muestra objetos grandes verdes y rojos en la misma parcela arbolada. La persistencia respalda que había objetos de escala vehicular o de carga, pero también es compatible con equipo almacenado; la atribución a vehículos de emergencia sigue sin resolverse.",
            "en": "The June 29 scene shows large green and red objects in the same tree-lined parcel. Persistence supports the presence of vehicle- or cargo-scale objects, but is also compatible with stored equipment; attribution to emergency vehicles remains unresolved.",
        },
        "limitations": {
            "es": "Cambios de color, ángulo y resolución impiden contar o tipificar los objetos de forma consistente.",
            "en": "Changes in colour, angle and resolution prevent consistent object counting or typing.",
        },
    },
    "ems_00119": {
        "reviewStatus": "not-discernible-in-followup",
        "finding": {
            "es": "La imagen del 29 de junio cubre el mismo sitio de escombros, pero el objeto amarillo parecido a excavadora del 26 de junio ya no se distingue en la misma posición junto a la vía. Pudo moverse o quedar oculto por geometría y resolución; la imagen no permite inferir trabajo realizado ni hora de salida.",
            "en": "The June 29 image covers the same debris site, but the June 26 yellow excavator-like object is no longer discernible at the same road-edge position. It may have moved or be masked by geometry and resolution; the image does not establish work performed or departure time.",
        },
        "limitations": {
            "es": "No visible en el seguimiento no significa ausente. La comparación es entre sensores y ángulos distintos.",
            "en": "Not visible in the follow-up does not mean absent. The comparison uses different sensors and viewing angles.",
        },
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_path(path: Path) -> str:
    return f"/{path.relative_to(ROOT / 'public').as_posix()}"


def upsert_source(sources: list[dict[str, Any]], source: dict[str, Any]) -> None:
    for index, existing in enumerate(sources):
        if existing["id"] == source["id"]:
            sources[index] = source
            return
    sources.append(source)


def upsert_event(events: list[dict[str, Any]], event: dict[str, Any]) -> None:
    for index, existing in enumerate(events):
        if existing["id"] == event["id"]:
            events[index] = event
            break
    else:
        events.append(event)
    events.sort(
        key=lambda item: datetime.fromisoformat(item["startsAt"].replace("Z", "+00:00"))
    )


def main() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text())
    timeline = json.loads(TIMELINE_PATH.read_text())
    reconstruction_catalog = json.loads(CATALOG_PATH.read_text())
    inventory = json.loads(INVENTORY_PATH.read_text())
    vantor_manifest = json.loads(VANTOR_MANIFEST_PATH.read_text())
    selected = {
        record["chipId"]: record
        for record in vantor_manifest["records"]
        if record["status"] == "human-reviewed-selected"
    }
    if set(selected) != set(FINDINGS):
        raise SystemExit(f"Selected temporal records differ from reviewed findings: {sorted(selected)}")

    evidence["updatedAt"] = UPDATED_AT
    summary = inventory["summary"]
    evidence["inventory"] = {
        "url": "/data/imagery/emsr884-acquisitions.json",
        "checkedAt": inventory["checkedAt"],
        "officialAois": summary["officialAoiRecords"],
        "localOpticalAois": summary["localOpticalAois"],
        "opticalProductRecords": summary["opticalProductImageRecords"],
        "distinctOpticalAcquisitions": summary["distinctOpticalAcquisitionEvents"],
        "publiclyReadableOpticalCogs": summary["publiclyReadableOpticalCogRecords"],
        "readableOpticalBytes": summary["readableOpticalBytes"],
        "countingNote": {
            "es": "Los registros de producto y las adquisiciones físicas no son lo mismo: AOI12 repite la escena del 26 de junio en PRODUCT y MONIT01. El inventario conserva ambos registros y publica un identificador de adquisición deduplicado.",
            "en": "Product records and physical acquisitions are not the same: AOI12 repeats the June 26 scene in PRODUCT and MONIT01. The inventory keeps both records and publishes a deduplicated acquisition identifier.",
        },
    }
    evidence["temporalReview"] = {
        "status": "human-reviewed",
        "summary": {
            "es": "El segundo producto oficial de AOI12, adquirido el 5 de julio, fue probado en las 26 ubicaciones candidatas. En los cinco sitios publicados no produjo una comparación de objetos utilizable: tres quedaron sin píxeles útiles y dos bajo nube o bruma. Escenas abiertas de Vantor del 27 y 29 de junio sí permitieron comparar los cinco sitios; son evidencia externa de triage, no conteos oficiales EMS.",
            "en": "The second official AOI12 product, acquired July 5, was tested at all 26 candidate locations. It yielded no usable object comparison at the five published sites: three lacked useful pixels and two were cloud- or haze-obscured. Open Vantor scenes from June 27 and 29 did support comparisons at all five sites; they are external triage evidence, not official EMS counts.",
        },
        "officialJuly5": {
            "acquisitionAt": "2026-07-05T15:05:00Z",
            "sensor": "GeoEye-1",
            "sourceId": "copernicus-aoi12-july-5",
            "candidateLocationsChecked": 26,
            "publishedSitesChecked": 5,
            "publishedSitesUsableForObjectComparison": 0,
            "finding": {
                "es": "La existencia de una adquisición posterior no equivale a cobertura útil. No se publican conclusiones temporales desde estos cinco recortes.",
                "en": "A later acquisition does not automatically provide useful coverage. No temporal conclusions are published from these five chips.",
            },
        },
        "externalFollowup": {
            "sourceIds": ["vantor-aoi12-june-27", "vantor-aoi12-june-29"],
            "publishedSitesChecked": 5,
            "usableComparisons": 5,
            "acquisitionDates": ["2026-06-27T13:48:10.374681Z", "2026-06-29T14:09:32.624709Z"],
            "finding": {
                "es": "Dos sitios occidentales tienen seguimiento del 27 de junio y tres sitios orientales del 29. Las comparaciones aportan persistencia o no discernibilidad, no propiedad, función ni suficiencia de la respuesta.",
                "en": "Two western sites have June 27 follow-up and three eastern sites have June 29 follow-up. The comparisons establish persistence or non-discernibility, not ownership, function or response adequacy.",
            },
        },
    }

    for observation in evidence["observations"]:
        chip_id = observation["chipId"]
        record = selected[chip_id]
        enhanced = TEMPORAL_PUBLIC_DIR / f"{chip_id}_{record['sceneId']}_swin2sr_x2.webp"
        if not enhanced.is_file():
            raise SystemExit(f"Missing temporal enhancement: {enhanced}")
        observation["temporalFollowup"] = {
            "acquisitionAt": record["acquisitionUtc"],
            "hoursAfterEvent": 64 if record["acquisitionUtc"].startswith("2026-06-27") else 112,
            "sourceId": (
                "vantor-aoi12-june-27"
                if record["acquisitionUtc"].startswith("2026-06-27")
                else "vantor-aoi12-june-29"
            ),
            "sensor": record["sensor"],
            "sourceRole": "external-triage",
            "reviewStatus": FINDINGS[chip_id]["reviewStatus"],
            "nativeImage": record["publicNativePath"],
            "enhancedImage": public_path(enhanced),
            "compareImage": record["publicComparePath"],
            "nativeSha256": record["publicNativeSha256"],
            "enhancedSha256": sha256(enhanced),
            "compareSha256": record["publicCompareSha256"],
            "finding": FINDINGS[chip_id]["finding"],
            "limitations": FINDINGS[chip_id]["limitations"],
        }

    EVIDENCE_PATH.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")

    sources = timeline["sources"]
    upsert_source(
        sources,
        {
            "id": "vantor-aoi12-june-27",
            "publisher": "Vantor Open Data",
            "title": "La Guaira LG05 post-event scene B15000110186C610",
            "publishedAt": "2026-06-27T13:48:10.374681Z",
            "url": f"{'https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev'}/vantor/venezuela-earthquake-jun-2026/B15000110186C610/B15000110186C610.tif",
            "type": "post-event-vhr-imagery",
            "evidenceClass": "primary",
            "license": "CC-BY-NC-4.0",
        },
    )
    upsert_source(
        sources,
        {
            "id": "vantor-aoi12-june-29",
            "publisher": "Vantor Open Data",
            "title": "La Guaira LG04 post-event scene B140001100B5C710",
            "publishedAt": "2026-06-29T14:09:32.624709Z",
            "url": f"{'https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev'}/vantor/venezuela-earthquake-jun-2026/B140001100B5C710/B140001100B5C710.tif",
            "type": "post-event-vhr-imagery",
            "evidenceClass": "primary",
            "license": "CC-BY-NC-4.0",
        },
    )
    upsert_source(
        sources,
        {
            "id": "copernicus-aoi12-july-5",
            "publisher": "Copernicus Emergency Management Service",
            "title": "EMSR884 AOI12 GeoEye-1 GRA_MONIT02 orthomosaic",
            "publishedAt": "2026-07-05T15:05:00Z",
            "url": "https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI12/GRA_MONIT02/EMSR884_AOI12_GRA_MONIT02_GEOEYE1_20260705_1505_ORTHO_cog.tif",
            "type": "official-post-event-vhr-imagery",
            "evidenceClass": "primary",
            "license": "Copernicus EMS public product terms",
        },
    )

    upsert_event(
        timeline["events"],
        {
            "id": "dated-aerial-followup-june-27-29",
            "startsAt": "2026-06-27T13:48:10.374681Z",
            "endsAt": "2026-06-29T14:09:32.624709Z",
            "timePrecision": "range",
            "phase": "assessment",
            "responseStage": "assessment",
            "first72Hours": True,
            "confidence": "single-source",
            "location": {
                "label": "La Guaira, Caraballeda y Catia La Mar",
                "precision": "cinco ubicaciones de chips EMS",
            },
            "title": {
                "es": "Cinco sitios reciben una segunda lectura aérea fechada",
                "en": "Five sites receive a second dated aerial reading",
            },
            "summary": {
                "es": "Escenas Vantor del 27 y 29 de junio permiten volver a observar los cinco sitios publicados. En dos patios industriales, la persistencia debilita la atribución a la respuesta. En Caraballeda oriental persisten objetos de escala de equipo en dos sitios; en el sitio de la probable excavadora, el objeto amarillo ya no es discernible el 29. Ninguna comparación establece operador, actividad ni suficiencia.",
                "en": "Vantor scenes from June 27 and 29 allow all five published sites to be observed again. At two industrial yards, persistence weakens response attribution. At two eastern Caraballeda sites, equipment-scale objects persist; at the probable-excavator site, the yellow object is no longer discernible on June 29. No comparison establishes operator, activity or adequacy.",
            },
            "sourceIds": ["vantor-aoi12-june-27", "vantor-aoi12-june-29"],
            "tags": ["aerial-imagery", "temporal-comparison", "vehicles", "heavy-machinery"],
            "image": {
                "src": selected["ems_00119"]["publicComparePath"],
                "alt": {
                    "es": "Comparación aérea del sitio ems_00119 entre el 26 y el 29 de junio",
                    "en": "Aerial comparison of site ems_00119 between June 26 and June 29",
                },
                "caption": {
                    "es": "Copernicus EMS, 26 jun / Vantor Open Data LG04, 29 jun. El objeto amarillo probable no es discernible en la imagen posterior; eso no demuestra ausencia.",
                    "en": "Copernicus EMS, June 26 / Vantor Open Data LG04, June 29. The probable yellow object is not discernible in the later image; that does not prove absence.",
                },
            },
        },
    )
    upsert_event(
        timeline["events"],
        {
            "id": "copernicus-july-5-coverage-test",
            "startsAt": "2026-07-05T15:05:00Z",
            "timePrecision": "minute",
            "phase": "assessment",
            "responseStage": "assessment",
            "first72Hours": False,
            "confidence": "confirmed",
            "location": {
                "label": "EMSR884 AOI12 Caraballeda",
                "precision": "huella oficial de adquisición",
            },
            "title": {
                "es": "La adquisición oficial del 5 de julio no cubre de forma útil los cinco sitios",
                "en": "The official July 5 acquisition does not usefully cover the five sites",
            },
            "summary": {
                "es": "El COG GeoEye-1 fue probado en las 26 ubicaciones candidatas. En los cinco sitios publicados, tres recortes no contienen píxeles útiles y dos están cubiertos por nube o bruma: cero permiten una comparación de objetos defendible. La fecha amplía el inventario, no la certeza sobre maquinaria o vehículos.",
                "en": "The GeoEye-1 COG was tested at all 26 candidate locations. At the five published sites, three chips contain no useful pixels and two are cloud- or haze-obscured: zero support a defensible object comparison. The date extends the inventory, not certainty about machinery or vehicles.",
            },
            "sourceIds": ["copernicus-aoi12-july-5"],
            "tags": ["aerial-imagery", "coverage-gap", "cloud", "no-data"],
        },
    )

    timeline["updatedAt"] = UPDATED_AT
    timeline["coverage"]["latestOpenSatelliteAt"] = "2026-07-05T15:05:00Z"
    timeline["coverage"]["note"] = {
        "es": "La cobertura es una reconstrucción de observaciones fechadas, no un registro continuo. Hay imagen pública de muy alta resolución hasta el 5 de julio, pero la adquisición oficial de ese día no aporta píxeles utilizables en los cinco sitios de respuesta publicados. Las conclusiones temporales de esos sitios usan escenas abiertas del 27 y 29 de junio y permanecen como evidencia externa de triage.",
        "en": "Coverage is a reconstruction from dated observations, not a continuous recording. Public very-high-resolution imagery extends through July 5, but that official acquisition supplies no usable pixels at the five published response sites. Temporal findings for those sites use open June 27 and 29 scenes and remain external triage evidence.",
    }
    timeline["events"].sort(
        key=lambda item: datetime.fromisoformat(item["startsAt"].replace("Z", "+00:00"))
    )
    TIMELINE_PATH.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n")

    for entry in reconstruction_catalog["entries"]:
        if entry["slug"] != "la-guaira":
            continue
        entry["updatedAt"] = UPDATED_AT
        entry["evidenceCutoff"] = timeline["coverage"]["latestEvidenceAt"]
        entry["eventCount"] = len(timeline["events"])
        entry["sourceCount"] = len(timeline["sources"])
        entry["imageEventCount"] = sum(1 for event in timeline["events"] if event.get("image"))
    reconstruction_catalog["updatedAt"] = UPDATED_AT
    CATALOG_PATH.write_text(json.dumps(reconstruction_catalog, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "updatedAt": UPDATED_AT,
                "observationsWithFollowup": len(evidence["observations"]),
                "timelineEvents": len(timeline["events"]),
                "timelineSources": len(timeline["sources"]),
                "distinctOpticalAcquisitions": evidence["inventory"]["distinctOpticalAcquisitions"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
