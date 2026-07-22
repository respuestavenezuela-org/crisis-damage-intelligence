#!/usr/bin/env python3
"""Publish human-adjudicated AOI12 temporal-grid findings and native imagery.

The VLM outputs are triage inputs only. This script publishes a deliberately
small set of findings that were checked against the dated, native-resolution
chips and, where stated, corroborated with a ground or official source.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
GRID_DIR = ROOT / "output" / "aoi12_temporal_response_grid" / "detail-250m" / "chips"
OPS_DIR = ROOT / "ops" / "data_acquisition_plan" / "aoi12_temporal_response_grid" / "detail-250m"
PUBLIC_DIR = ROOT / "public" / "data" / "reconstruction" / "evidence" / "la-guaira" / "grid"
AERIAL_PATH = ROOT / "public" / "data" / "reconstruction" / "aerial-response-evidence-la-guaira.json"
TIMELINE_PATH = ROOT / "public" / "data" / "reconstruction" / "la-guaira-timeline.json"
CATALOG_PATH = ROOT / "public" / "data" / "reconstruction" / "catalog.json"

JUNE26 = "COPERNICUS_LEGION_20260626.png"
JUNE29_WEST = "VANTOR_B140001100B5C810_20260629.png"
JUNE29_EAST = "VANTOR_B140001100B5C710_20260629.png"


SITES = [
    {
        "slug": "caraballeda-golf",
        "cell_id": "aoi12_r018_c111",
        "june29": JUNE29_EAST,
        "status": "likely-response-related",
        "confidence": "corroborated",
        "category": "site-use",
        "location": {
            "label": "Campo de golf de Caraballeda · Urbanización Caribe",
            "latitude": 10.61411884,
            "longitude": -66.8425174,
            "precision": "centro de celda de 250 m",
        },
        "title": {
            "es": "El campo de golf ya concentraba una operación de respuesta a +41 h",
            "en": "The golf course already held a response operation by +41 h",
        },
        "finding": {
            "es": (
                "En la imagen oficial del 26 de junio aparecen vehículos y objetos rectangulares "
                "organizados sobre un terreno que estaba casi vacío antes del sismo. La imagen por sí "
                "sola no prueba que allí durmieran personas; reportes de terreno del 28 de junio "
                "identificaron el campo de golf como hospital, helipuerto y refugio."
            ),
            "en": (
                "The official June 26 image shows vehicles and organized rectangular objects on ground "
                "that was largely empty before the earthquakes. Imagery alone does not prove that people "
                "slept there; June 28 ground reporting identified the golf course as a hospital, helipad "
                "and shelter."
            ),
        },
        "followup": {
            "reviewStatus": "supports-new-response-site",
            "finding": {
                "es": (
                    "Dos escenas independientes del 29 de junio muestran una instalación mucho más "
                    "definida: carpas o módulos temporales, vehículos y áreas ordenadas en arcos. Fuentes "
                    "posteriores describen familias alojadas y un puesto de operaciones militares en el lugar."
                ),
                "en": (
                    "Two independent June 29 scenes show a much more developed installation: temporary "
                    "tents or modules, vehicles and organized arc-shaped areas. Later sources describe "
                    "sheltered families and a military operations post at the site."
                ),
            },
            "limitations": {
                "es": (
                    "La imagen no permite contar personas, separar usos civiles y operativos ni medir "
                    "la suficiencia de la atención."
                ),
                "en": (
                    "The image cannot count people, separate civilian and operational uses, or measure "
                    "the adequacy of assistance."
                ),
            },
        },
        "sourceIds": [
            "copernicus-aoi12-june-26",
            "vantor-aoi12-june-29",
            "panorama-golf-june-28",
            "vtv-golf-july-9",
        ],
    },
    {
        "slug": "estadio-jorge-garcia",
        "cell_id": "aoi12_r013_c083",
        "june29": JUNE29_WEST,
        "status": "likely-response-related",
        "confidence": "corroborated",
        "category": "site-use",
        "location": {
            "label": "Estadio Jorge Luis García Carneiro · Macuto",
            "latitude": 10.60308183,
            "longitude": -66.90539947,
            "precision": "centro de celda de 250 m",
        },
        "title": {
            "es": "Un equipo médico y campamento ocupan el estadio entre el 26 y el 29",
            "en": "A medical team and camp occupy the stadium between June 26 and 29",
        },
        "finding": {
            "es": (
                "El terreno del estadio aparece casi libre de estructuras temporales el 26 de junio. "
                "El 29 contiene filas densas de carpas o módulos, áreas organizadas y numerosos vehículos; "
                "un estacionamiento contiguo también está ocupado. OPS/OMS situó allí un equipo médico "
                "fijo de Cruz Roja en su mapa de despliegue al 2 de julio."
            ),
            "en": (
                "The stadium field is largely free of temporary structures on June 26. By June 29 it "
                "contains dense rows of tents or modules, organized areas and many vehicles; an adjacent "
                "parking lot is also occupied. PAHO/WHO placed a fixed Red Cross medical team there in "
                "its deployment map as of July 2."
            ),
        },
        "followup": {
            "reviewStatus": "supports-new-response-site",
            "finding": {
                "es": (
                    "La transición ocurre dentro del intervalo de imágenes del 26 al 29 de junio. "
                    "La adquisición del 29 confirma presencia y organización, no la hora exacta de apertura."
                ),
                "en": (
                    "The transition occurs within the June 26–29 image interval. The June 29 acquisition "
                    "confirms presence and organization, not the exact opening time."
                ),
            },
            "limitations": {
                "es": (
                    "Las cubiertas no permiten distinguir desde el aire áreas médicas, alojamiento, "
                    "almacenamiento u otros usos internos."
                ),
                "en": (
                    "Roof coverings do not allow medical, sleeping, storage or other internal uses to "
                    "be separated from the air."
                ),
            },
        },
        "sourceIds": [
            "copernicus-aoi12-june-26",
            "vantor-aoi12-june-29",
            "paho-emt-july-2",
        ],
    },
    {
        "slug": "punta-mulatos-waterfront",
        "cell_id": "aoi12_r013_c073",
        "june29": JUNE29_WEST,
        "status": "likely-response-related",
        "confidence": "inferred",
        "category": "site-use",
        "location": {
            "label": "Frente costero de Punta de Mulatos · La Guaira",
            "latitude": 10.60308183,
            "longitude": -66.92785735,
            "precision": "centro de celda de 250 m",
        },
        "title": {
            "es": "Módulos temporales ocupan un estacionamiento costero el 29 de junio",
            "en": "Temporary modules occupy a waterfront parking lot on June 29",
        },
        "finding": {
            "es": (
                "El estacionamiento tenía pocos objetos en la imagen del 26. El 29 muestra filas de "
                "grandes módulos blancos, vehículos y una organización interna nueva, compatible con "
                "campamento médico, logístico o de alojamiento. La función exacta no se resuelve en la imagen."
            ),
            "en": (
                "The parking lot held few objects in the June 26 image. On June 29 it shows rows of large "
                "white modules, vehicles and a new internal layout compatible with a medical, logistics or "
                "accommodation camp. The exact function is unresolved in the imagery."
            ),
        },
        "followup": {
            "reviewStatus": "supports-new-response-site",
            "finding": {
                "es": (
                    "La aparición está acotada al intervalo del 26 al 29 de junio. El sitio es cercano "
                    "al sector costero donde fuentes posteriores ubican despliegues de respuesta, pero "
                    "no se atribuye aquí a una organización."
                ),
                "en": (
                    "The appearance is bounded to the June 26–29 interval. The site is near the waterfront "
                    "sector where later sources place response deployments, but no organization is attributed here."
                ),
            },
            "limitations": {
                "es": "No hay identificación visual legible, y la imagen no muestra el interior de los módulos.",
                "en": "No readable identification is visible, and the image does not show inside the modules.",
            },
        },
        "sourceIds": ["copernicus-aoi12-june-26", "vantor-aoi12-june-29"],
    },
    {
        "slug": "el-palmar-track",
        "cell_id": "aoi12_r019_c103",
        "june29": JUNE29_WEST,
        "status": "likely-response-related",
        "confidence": "inferred",
        "category": "site-use",
        "location": {
            "label": "Pista costera · El Palmar Oeste, Caraballeda",
            "latitude": 10.61632619,
            "longitude": -66.8604837,
            "precision": "centro de celda de 250 m",
        },
        "title": {
            "es": "Una pista deportiva se convierte en sitio temporal organizado",
            "en": "A sports track becomes an organized temporary site",
        },
        "finding": {
            "es": (
                "La pista está esencialmente libre el 26 de junio. El 29 contiene una fila central de "
                "módulos blancos, carpas periféricas, vehículos y circulación organizada. El cambio y el "
                "contexto son compatibles con uso de respuesta, sin resolver operador ni función."
            ),
            "en": (
                "The track is essentially clear on June 26. On June 29 it contains a central row of white "
                "modules, peripheral tents, vehicles and organized circulation. The change and context are "
                "consistent with response use, without resolving operator or function."
            ),
        },
        "followup": {
            "reviewStatus": "supports-new-response-site",
            "finding": {
                "es": "La instalación aparece entre el 26 y el 29 y está activa en la única imagen posterior utilizable.",
                "en": "The installation appears between June 26 and 29 and is active in the only usable later image.",
            },
            "limitations": {
                "es": "Una sola adquisición posterior no establece duración, capacidad ni uso nocturno.",
                "en": "A single usable later acquisition does not establish duration, capacity or overnight use.",
            },
        },
        "sourceIds": ["copernicus-aoi12-june-26", "vantor-aoi12-june-29"],
    },
    {
        "slug": "los-corales-vehicle-lot",
        "cell_id": "aoi12_r019_c107",
        "june29": JUNE29_WEST,
        "status": "unresolved",
        "confidence": "inferred",
        "category": "large-vehicles",
        "location": {
            "label": "Lote abierto · Los Corales, Caraballeda",
            "latitude": 10.61632619,
            "longitude": -66.85150055,
            "precision": "centro de celda de 250 m",
        },
        "title": {
            "es": "Vehículos grandes aparecen ordenados en un lote a +41 h",
            "en": "Large vehicles appear in ordered rows on an open lot by +41 h",
        },
        "finding": {
            "es": (
                "Un lote vacío antes del sismo contiene aproximadamente una quincena de objetos de escala "
                "vehicular en filas en la imagen del 26 de junio. El patrón es compatible con estacionamiento "
                "o staging, pero no permite clasificar camiones, ambulancias, maquinaria ni propiedad."
            ),
            "en": (
                "A lot that was empty before the earthquakes contains roughly fifteen vehicle-scale objects "
                "in rows in the June 26 image. The pattern is compatible with parking or staging, but does not "
                "support classifying trucks, ambulances, machinery or ownership."
            ),
        },
        "followup": {
            "reviewStatus": "supports-object-persistence",
            "finding": {
                "es": (
                    "El 29 de junio el grupo permanece, con una disposición parcialmente reorganizada. "
                    "La persistencia confirma objetos móviles de gran escala, no su papel en la respuesta."
                ),
                "en": (
                    "On June 29 the group remains, in a partially reorganized layout. Persistence confirms "
                    "large mobile objects, not their role in the response."
                ),
            },
            "limitations": {
                "es": "La resolución y el ángulo no permiten tipificar cada vehículo ni saber si operó en otro sitio.",
                "en": "Resolution and viewing angle do not support typing each vehicle or knowing whether it operated elsewhere.",
            },
        },
        "sourceIds": ["copernicus-aoi12-june-26", "vantor-aoi12-june-29"],
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_native(cell_id: str, scene_name: str, destination_name: str) -> tuple[str, str]:
    source = GRID_DIR / cell_id / scene_name
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = PUBLIC_DIR / destination_name
    shutil.copyfile(source, destination)
    public_path = "/" + str(destination.relative_to(ROOT / "public"))
    return public_path, sha256(destination)


def compare_images(left_path: Path, right_path: Path, destination_name: str) -> tuple[str, str]:
    left = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")
    if left.size != right.size:
        raise ValueError(f"Native comparison dimensions differ: {left.size} != {right.size}")
    comparison = Image.new("RGB", (left.width + right.width, left.height), (20, 20, 18))
    comparison.paste(left, (0, 0))
    comparison.paste(right, (left.width, 0))
    destination = PUBLIC_DIR / destination_name
    comparison.save(destination, "WEBP", quality=92, method=6)
    public_path = "/" + str(destination.relative_to(ROOT / "public"))
    return public_path, sha256(destination)


def build_observation(site: dict[str, Any]) -> dict[str, Any]:
    slug = site["slug"]
    cell_id = site["cell_id"]
    native_path, native_hash = copy_native(cell_id, JUNE26, f"{slug}_20260626_native.png")
    followup_path, followup_hash = copy_native(
        cell_id,
        site["june29"],
        f"{slug}_20260629_native.png",
    )
    compare_path, compare_hash = compare_images(
        GRID_DIR / cell_id / JUNE26,
        GRID_DIR / cell_id / site["june29"],
        f"{slug}_20260626_20260629_compare.webp",
    )
    return {
        "id": f"aerial-grid-{slug}",
        "chipId": cell_id,
        "status": site["status"],
        "confidence": site["confidence"],
        "category": site["category"],
        "location": site["location"],
        "title": site["title"],
        "finding": site["finding"],
        "nativeImage": native_path,
        "nativeSha256": native_hash,
        "mapUrl": (
            "https://www.google.com/maps/search/?api=1&query="
            f"{site['location']['latitude']},{site['location']['longitude']}"
        ),
        "sourceIds": site["sourceIds"],
        "temporalFollowup": {
            "acquisitionAt": "2026-06-29T14:09:32Z"
            if site["june29"] == JUNE29_EAST
            else "2026-06-29T14:09:55Z",
            "hoursAfterEvent": 112,
            "sourceId": "vantor-aoi12-june-29",
            "sensor": "LG04",
            "sourceRole": "external-triage",
            "reviewStatus": site["followup"]["reviewStatus"],
            "nativeImage": followup_path,
            "compareImage": compare_path,
            "nativeSha256": followup_hash,
            "compareSha256": compare_hash,
            "finding": site["followup"]["finding"],
            "limitations": site["followup"]["limitations"],
        },
    }


def upsert_by_id(items: list[dict[str, Any]], new_item: dict[str, Any]) -> None:
    for index, item in enumerate(items):
        if item.get("id") == new_item["id"]:
            items[index] = new_item
            return
    items.append(new_item)


def update_aerial(now: str, observations: list[dict[str, Any]]) -> None:
    payload = json.loads(AERIAL_PATH.read_text(encoding="utf-8"))
    payload["updatedAt"] = now
    payload["gridReview"] = {
        "status": "human-reviewed",
        "profile": "detail-250m",
        "geography": {
            "es": "Corredor La Guaira–Macuto–Caraballeda, con celdas alrededor del daño oficial EMS",
            "en": "La Guaira–Macuto–Caraballeda corridor, using cells around official EMS damage",
        },
        "resolution": {
            "cellSizeMeters": 250,
            "chipPixels": 768,
            "outputGroundSampleDistanceMeters": 0.3255,
            "sourceGroundSampleDistanceMeters": "aprox. 0,35–0,50",
            "superResolutionUsedForEvidence": False,
            "policy": {
                "es": (
                    "Cada chip conserva píxeles fuente a una escala cercana a la resolución nativa. "
                    "No se usó superresolución para detectar ni validar objetos; las mejoras 2× antiguas "
                    "siguen separadas y solo sirven para visualización."
                ),
                "en": (
                    "Each chip preserves source pixels at a scale close to native resolution. "
                    "No super-resolution was used to detect or validate objects; earlier 2× derivatives "
                    "remain separate and are display-only."
                ),
            },
        },
        "coverage": {
            "gridCellsConsidered": 1022,
            "gridCellsAnalyzed": 734,
            "gridCellsRejectedForCoverageOrQuality": 288,
            "primaryModelLikely": 16,
            "primaryModelPossible": 171,
            "priorityCells": 226,
            "secondaryModelReviewed": 226,
            "crossModelPositiveAgreements": 46,
            "priorityCellsHumanReviewed": 55,
            "newPublishedSites": len(observations),
        },
        "models": {
            "primary": {
                "provider": "Hugging Face Inference Router",
                "modelId": "Qwen/Qwen3-VL-30B-A3B-Instruct",
                "records": 734,
            },
            "secondary": [
                {
                    "provider": "Hugging Face Inference Router",
                    "modelId": "Qwen/Qwen2.5-VL-72B-Instruct",
                    "records": 206,
                },
                {
                    "provider": "Hugging Face Inference Router",
                    "modelId": "CohereLabs/command-a-vision-07-2025",
                    "records": 20,
                },
            ],
            "minimax": {
                "status": "not-run-provider-credential-unavailable",
                "role": "optional selective adjudicator, never the sole basis for publication",
            },
        },
        "calibration": {
            "es": (
                "El pase inicial de 500 m a ~0,98 m/píxel produjo falsos positivos y se conservó solo "
                "como calibración. En el pase de detalle, 46 acuerdos positivos entre modelos fueron "
                "revisados a píxel nativo; varios acuerdos en patios industriales y zonas de destrucción "
                "seguían siendo falsos. El acuerdo de modelos no sustituye la revisión humana."
            ),
            "en": (
                "The initial 500 m pass at about 0.98 m/pixel produced false positives and is retained "
                "only as calibration. In the detail pass, 46 positive model agreements were checked at "
                "native pixels; several agreements in industrial yards and destruction zones were still "
                "false. Model agreement does not replace human review."
            ),
        },
    }
    payload["review"]["method"] = {
        "es": (
            "Además de la cola anterior de 26 chips EMS, se dividió el corredor en 1.022 celdas de 250 m. "
            "Se analizaron 734 celdas con cobertura útil a 768 px (~0,326 m/píxel), se adjudicaron 226 "
            "prioridades con un segundo VLM y se revisaron manualmente 55 celdas de mayor señal o acuerdo. "
            "Solo se publican cambios defendibles en píxeles nativos."
        ),
        "en": (
            "In addition to the earlier 26-chip EMS queue, the corridor was divided into 1,022 250 m cells. "
            "The 734 cells with useful coverage were analyzed at 768 px (~0.326 m/pixel), 226 priority cells "
            "were adjudicated by a second VLM, and 55 highest-signal or agreement cells were manually reviewed. "
            "Only changes supportable in native pixels are published."
        ),
    }
    payload["review"]["summary"] = {
        "es": (
            "La revisión ampliada identifica cuatro nuevos sitios temporales compatibles con respuesta: "
            "el campo de golf de Caraballeda ya activo a +41 h, y para el 29 de junio el Estadio Jorge "
            "García, un lote costero en Punta de Mulatos y una pista en El Palmar. Un quinto lote muestra "
            "vehículos grandes desde +41 h, pero su función sigue sin resolver."
        ),
        "en": (
            "The expanded review identifies four new temporary sites consistent with response use: "
            "the Caraballeda golf course already active at +41 h, and by June 29 the Jorge García Stadium, "
            "a Punta de Mulatos waterfront lot and an El Palmar track. A fifth lot shows large vehicles "
            "from +41 h, but their function remains unresolved."
        ),
    }
    payload["review"]["absenceCaveat"] = {
        "es": (
            "El barrido cubre el corredor oficial y fechas concretas, no cada calle ni cada hora. "
            "No ver un objeto no demuestra ausencia, y la imagen no permite medir suficiencia."
        ),
        "en": (
            "The scan covers the official corridor and specific dates, not every street or every hour. "
            "Failure to see an object does not prove absence, and imagery cannot measure adequacy."
        ),
    }

    published = payload["observations"]
    for observation in observations:
        upsert_by_id(published, observation)

    candidate_ids = payload["review"]["candidateIds"]
    for observation in observations:
        if observation["chipId"] not in candidate_ids:
            candidate_ids.append(observation["chipId"])
    payload["review"]["candidateRecords"] = len(candidate_ids)
    payload["review"]["publishedSites"] = len(published)
    payload["review"]["likelyResponseSites"] = sum(
        item["status"] == "likely-response-related" for item in published
    )
    payload["review"]["unresolvedSites"] = sum(item["status"] == "unresolved" for item in published)
    payload["review"]["confidentCollectionCentres"] = 0
    payload["review"]["confidentSheltersOrSleepingSites"] = 1
    AERIAL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_timeline(now: str, observations: list[dict[str, Any]]) -> None:
    payload = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    payload["updatedAt"] = now
    payload["coverage"]["note"] = {
        "es": (
            "La cobertura es una reconstrucción de observaciones fechadas, no un registro continuo. "
            "El nuevo barrido usa 734 celdas útiles de 250 m a ~0,326 m/píxel y compara el 26 con el 29 de junio. "
            "La adquisición oficial del 5 de julio sigue limitada por nubes o falta de píxeles en estos sitios."
        ),
        "en": (
            "Coverage is a reconstruction from dated observations, not a continuous recording. "
            "The new scan uses 734 useful 250 m cells at ~0.326 m/pixel and compares June 26 with June 29. "
            "The official July 5 acquisition remains limited by cloud or missing pixels at these sites."
        ),
    }
    payload["first72Assessment"]["summary"] = {
        "es": (
            "La respuesta local y civil comenzó de inmediato. El 25 de junio la ONU describía equipos "
            "internacionales entrantes; el 26 hablaba de decenas de equipos en despliegue. Una imagen "
            "Copernicus del 26, unas 41 horas después, muestra vehículos, una probable excavadora junto "
            "a escombros y una concentración organizada nueva en el campo de golf de Caraballeda. "
            "Reportes de terreno del 28 identificaron ese campo como hospital, helipuerto y refugio. "
            "El mismo 26, periodismo en terreno reportó caravanas hacia La Guaira y residentes excavando "
            "con pocos equipos visibles. La evidencia prueba llegada a sitios concretos, no cobertura uniforme."
        ),
        "en": (
            "Local and civilian response began immediately. On June 25 the UN described incoming "
            "international teams; on June 26 it described dozens of teams deploying. A June 26 Copernicus "
            "image, about 41 hours after the earthquakes, shows vehicles, a probable excavator beside debris "
            "and a new organized concentration at the Caraballeda golf course. June 28 ground reporting "
            "identified that course as a hospital, helipad and shelter. The same day, field journalism "
            "reported convoys toward La Guaira and residents digging with few teams visible. The evidence "
            "establishes arrival at specific sites, not uniform coverage."
        ),
    }

    source_items = [
        {
            "id": "panorama-golf-june-28",
            "publisher": "Panorama",
            "title": "Caraballeda golf course converted into hospital, helipad and shelter",
            "publishedAt": "2026-06-28T21:21:00-04:00",
            "url": (
                "https://panorama.onl/sucesos/caraballeda-el-campo-de-golf-de-la-guaira-"
                "convertido-en-refugio-tras-los-terremotos-20260628-2221.html"
            ),
            "type": "field-reporting",
            "evidenceClass": "secondary",
            "license": "Copyright; link only",
        },
        {
            "id": "paho-emt-july-2",
            "publisher": "PAHO/WHO",
            "title": "Venezuela earthquake Emergency Medical Team deployment map, 2 July 2026",
            "publishedAt": "2026-07-02T23:59:00-04:00",
            "url": (
                "https://www.paho.org/sites/default/files/2026/07/"
                "emt-response-venezuela-earthquakes-02062026-v3.pdf"
            ),
            "type": "official-deployment-map",
            "evidenceClass": "primary",
            "license": "Link and attribution",
        },
        {
            "id": "vtv-golf-july-9",
            "publisher": "Venezolana de Televisión",
            "title": "FANB operations post at the Caraballeda golf course",
            "publishedAt": "2026-07-09T12:00:00-04:00",
            "url": "https://vtv.com.ve/presidenta-e-delcy-rodriguez-supervisa-despliegue-de-fanb-en-caraballeda/",
            "type": "government-update",
            "evidenceClass": "primary",
            "license": "Link and attribution",
        },
    ]
    for source in source_items:
        upsert_by_id(payload["sources"], source)

    golf = next(item for item in observations if item["id"] == "aerial-grid-caraballeda-golf")
    stadium = next(item for item in observations if item["id"] == "aerial-grid-estadio-jorge-garcia")
    golf_finding = {
        "id": "golf-course-response-by-41-hours",
        "status": "observed-site",
        "confidence": "corroborated",
        "title": {
            "es": "Un centro de respuesta ya era visible en el campo de golf a +41 h",
            "en": "A response centre was already visible at the golf course by +41 h",
        },
        "body": {
            "es": (
                "La imagen del 26 muestra una concentración organizada que no estaba en el baseline. "
                "Reportes del 28 identifican el lugar como hospital, helipuerto y refugio. Esto acota "
                "presencia en el sitio a +41 h, pero no la hora de apertura ni su capacidad."
            ),
            "en": (
                "The June 26 image shows an organized concentration absent from the baseline. June 28 "
                "reporting identifies the site as a hospital, helipad and shelter. This bounds site presence "
                "to +41 h, but not opening time or capacity."
            ),
        },
        "sourceIds": ["copernicus-aoi12-june-26", "panorama-golf-june-28"],
        "image": {
            "src": golf["temporalFollowup"]["compareImage"],
            "alt": {
                "es": "Comparación del campo de golf de Caraballeda entre el 26 y el 29 de junio.",
                "en": "Comparison of the Caraballeda golf course between June 26 and June 29.",
            },
            "caption": {
                "es": "Copernicus EMS 26 jun / Vantor Open Data 29 jun. Celdas de 250 m a ~0,326 m/píxel; sin superresolución.",
                "en": "Copernicus EMS June 26 / Vantor Open Data June 29. 250 m cells at ~0.326 m/pixel; no super-resolution.",
            },
        },
    }
    upsert_by_id(payload["first72Assessment"]["findings"], golf_finding)

    event = {
        "id": "organized-response-sites-june-29",
        "startsAt": "2026-06-29T10:09:55-04:00",
        "timePrecision": "minute",
        "phase": "shelter",
        "responseStage": "observed-site",
        "first72Hours": False,
        "confidence": "corroborated",
        "location": {
            "label": "La Guaira, Macuto y Caraballeda",
            "precision": "cinco celdas de 250 m",
        },
        "title": {
            "es": "El 29 de junio aparecen varios sitios temporales organizados",
            "en": "Several organized temporary sites are visible on June 29",
        },
        "summary": {
            "es": (
                "El barrido temporal de 734 celdas muestra instalaciones nuevas en el Estadio Jorge García, "
                "un lote costero de Punta de Mulatos y una pista de El Palmar; el campo de golf de Caraballeda "
                "se expande. Las fuentes terrestres corroboran función de respuesta en el estadio y el campo "
                "de golf. En los otros sitios, función y operador siguen inferidos."
            ),
            "en": (
                "The 734-cell temporal scan shows new installations at Jorge García Stadium, a Punta de "
                "Mulatos waterfront lot and an El Palmar track; the Caraballeda golf-course site expands. "
                "Ground sources corroborate response functions at the stadium and golf course. Function and "
                "operator at the other sites remain inferred."
            ),
        },
        "sourceIds": [
            "copernicus-aoi12-june-26",
            "vantor-aoi12-june-29",
            "panorama-golf-june-28",
            "paho-emt-july-2",
        ],
        "tags": ["aerial-imagery", "temporary-sites", "shelter", "medical", "logistics"],
        "image": {
            "src": stadium["temporalFollowup"]["compareImage"],
            "alt": {
                "es": "Comparación del Estadio Jorge García entre el 26 y el 29 de junio.",
                "en": "Comparison of Jorge García Stadium between June 26 and June 29.",
            },
            "caption": {
                "es": "Copernicus EMS 26 jun / Vantor Open Data 29 jun. El campo pasa de casi vacío a una instalación temporal densa.",
                "en": "Copernicus EMS June 26 / Vantor Open Data June 29. The field changes from largely empty to a dense temporary installation.",
            },
        },
    }
    upsert_by_id(payload["events"], event)
    payload["events"].sort(
        key=lambda item: datetime.fromisoformat(item["startsAt"].replace("Z", "+00:00")).astimezone(timezone.utc)
    )
    TIMELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_catalog(now: str) -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    timeline = json.loads(TIMELINE_PATH.read_text(encoding="utf-8"))
    catalog["updatedAt"] = now
    for entry in catalog["entries"]:
        if entry["slug"] != "la-guaira":
            continue
        entry["updatedAt"] = now
        entry["eventCount"] = len(timeline["events"])
        entry["sourceCount"] = len(timeline["sources"])
        entry["imageEventCount"] = sum(bool(item.get("image")) for item in timeline["events"])
        entry["gaps"] = [
            {
                "es": "Hora exacta de apertura y capacidad de los sitios temporales observados",
                "en": "Exact opening time and capacity of observed temporary sites",
            },
            {
                "es": "Propiedad, función y tiempo de operación de maquinaria y vehículos visibles",
                "en": "Ownership, function and operating time of visible machinery and vehicles",
            },
        ]
        break
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    required = [
        OPS_DIR / "manifest.json",
        OPS_DIR / "hf_primary.jsonl",
        OPS_DIR / "hf_secondary_adjudication.jsonl",
        OPS_DIR / "human_review_queue_agreement.json",
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Required reviewed-grid artifacts missing: {missing}")

    observations = [build_observation(site) for site in SITES]
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    update_aerial(now, observations)
    update_timeline(now, observations)
    update_catalog(now)
    print(
        json.dumps(
            {
                "publishedObservations": len(observations),
                "publicDirectory": str(PUBLIC_DIR.relative_to(ROOT)),
                "aerialEvidence": str(AERIAL_PATH.relative_to(ROOT)),
                "timeline": str(TIMELINE_PATH.relative_to(ROOT)),
                "catalog": str(CATALOG_PATH.relative_to(ROOT)),
                "updatedAt": now,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
