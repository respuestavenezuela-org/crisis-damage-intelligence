#!/usr/bin/env python3
"""Build a public, source-bounded MapAction response-site evidence package."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "mapaction_response_sites"
)
PUBLIC_OUTPUT = (
    ROOT
    / "public"
    / "data"
    / "reconstruction"
    / "mapaction-response-sites-la-guaira.json"
)
PUBLIC_CANDIDATES = (
    ROOT
    / "public"
    / "data"
    / "reconstruction"
    / "full-pilot-response-evidence.jsonl"
)


SITE_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "polideportivo-jose-maria-vargas",
        "name": "Campamento Transitorio Polideportivo José María Vargas",
        "longitude": -66.9704694,
        "latitude": 10.6002944,
        "documentedAsOf": "2026-07-07",
        "mapProductId": "2026-ven-001-ma018-v3",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma018-v3",
        "pdfUrl": "https://maps.mapaction.org/dataset/3a006c73-089a-48d1-bb11-c43579f42f6e/resource/1d1f33e8-81b6-495d-bad2-136dc4045699/download/ma018_shelter_polideportivo_guaira_vargas_v03-300dp.pdf",
        "imageUrl": "https://maps.mapaction.org/dataset/3a006c73-089a-48d1-bb11-c43579f42f6e/resource/0489203e-2b6a-4c78-9045-5ba910007d8d/download/ma018_shelter_polideportivo_guaira_vargas_v03-300dpi.jpg",
        "directlyAnnotatedServices": [
            "oficina de registro y coordinación",
            "comedor y área de comida",
            "puesto de salud",
            "ambulatorio",
            "bodega de Naciones Unidas",
            "bodega de artículos no alimentarios",
            "espacio seguro para niños y niñas",
            "letrinas y puntos de basura",
            "entrada peatonal y entrada vehicular",
        ],
        "sleepingEvidence": {
            "annotatedSleepingAreas": 11,
            "description": "Un dormitorio principal y dormitorios numerados del 1 al 10.",
        },
    },
    {
        "id": "playa-grande",
        "name": "Campamento Transitorio Playa Grande",
        "longitude": -67.0159852,
        "latitude": 10.6079817,
        "documentedAsOf": "2026-07-07",
        "mapProductId": "2026-ven-001-ma022-v2",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma022-v2",
        "pdfUrl": "https://maps.mapaction.org/dataset/9ac24c43-fa2d-4c51-8aa2-49f940dbeb46/resource/ef496355-ac82-48ea-b90e-3520cb5a01d8/download/ma022-v02-shelter_playa_grande-300dpi.pdf",
        "imageUrl": "https://maps.mapaction.org/dataset/9ac24c43-fa2d-4c51-8aa2-49f940dbeb46/resource/47dd6d78-6e78-45a0-a9d2-00425bc60006/download/ma022-v02-shelter_playa_grande-300dpi.jpg",
        "directlyAnnotatedServices": [
            "distribución de comida",
            "comedor del Programa Mundial de Alimentos",
            "puesto de salud",
            "letrinas",
            "dos espacios seguros para niños y niñas",
            "entrada",
        ],
        "sleepingEvidence": {
            "annotatedSleepingAreas": 1,
            "description": "Una estructura comunal etiquetada como dormitorio.",
        },
    },
    {
        "id": "estadio-cesar-nieves",
        "name": "Campamento Transitorio Estadio César Nieves",
        "longitude": -67.0229282,
        "latitude": 10.602448,
        "documentedAsOf": "2026-07-07",
        "mapProductId": "2026-ven-001-ma023-v3",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma023-v3",
        "pdfUrl": "https://maps.mapaction.org/dataset/456f5f96-4754-4774-abe0-0fd47d995338/resource/57336fcd-f95a-49c3-a2a9-7b981b6e9c48/download/ma023-v03-shelter_estadio_cesar_nieves-300dpi.pdf",
        "imageUrl": "https://maps.mapaction.org/dataset/456f5f96-4754-4774-abe0-0fd47d995338/resource/75fd716e-a53f-4eee-adea-7e39d8595df6/download/ma023-v03-shelter_estadio_cesar_nieves-300dpi.jpg",
        "directlyAnnotatedServices": [
            "distribución de agua",
            "registro",
            "ambulatorio de salud",
            "puesto de salud",
            "comedor",
            "dos áreas de letrinas",
            "espacio seguro para niños y niñas",
            "entrada",
        ],
        "sleepingEvidence": {
            "annotatedSleepingAreas": 1,
            "description": "Una estructura comunal etiquetada como dormitorio.",
        },
    },
    {
        "id": "mare-abajo",
        "name": "Campamento Transitorio Mare Abajo",
        "longitude": -66.9807639,
        "latitude": 10.6080861,
        "documentedAsOf": "2026-07-11",
        "mapProductId": "2026-ven-001-ma044-v1",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma044-v1",
        "pdfUrl": "https://maps.mapaction.org/dataset/4f75da0b-4286-4a66-b753-3edc51c70502/resource/c71167c1-7bd5-487f-82c1-5e803d171588/download/ma044_mare_abajo_surround-300dpi.pdf",
        "imageUrl": "https://maps.mapaction.org/dataset/4f75da0b-4286-4a66-b753-3edc51c70502/resource/d551f7a1-edb9-4f12-bf6a-2f60120f519f/download/ma044_mare_abajo_surround-300dpi.jpg",
        "directlyAnnotatedServices": [],
        "sleepingEvidence": {
            "annotatedSleepingAreas": 0,
            "description": "El producto delimita el campamento con imagen de dron, pero no etiqueta funciones internas.",
        },
    },
    {
        "id": "campo-golf-caraballeda",
        "name": "Campo de Golf de Caraballeda",
        "longitude": -66.8422005,
        "latitude": 10.6138506,
        "documentedAsOf": "2026-07-04",
        "mapProductId": "2026-ven-001-ma032-v1",
        "datasetUrl": "https://maps.mapaction.org/dataset/2026-ven-001-ma032-v1",
        "pdfUrl": "https://maps.mapaction.org/dataset/e73cfed9-b9b1-498b-8501-034e5b6ac08c/resource/3ccca4f3-682c-4efa-8446-f1c10082d0c3/download/ma032_shelter_carballeda_campo_golf-300dpi.pdf",
        "imageUrl": "https://maps.mapaction.org/dataset/e73cfed9-b9b1-498b-8501-034e5b6ac08c/resource/eb97c5a7-af0f-46bd-ac44-5079c2c7818c/download/ma032_shelter_carballeda_campo_golf-300dpi.jpg",
        "directlyAnnotatedServices": [
            "puesto de salud mexicano",
            "laboratorio y rayos X",
            "distribución de comida",
            "presencia señalada de UNICEF",
            "presencia señalada de Johanniter",
            "entrada",
            "dos áreas marcadas con símbolo de helipuerto",
        ],
        "sleepingEvidence": {
            "annotatedSleepingAreas": 0,
            "description": "Este producto documenta servicios humanitarios, no un inventario de dormitorios.",
        },
    },
)

CAPACITY_LABELS = (
    ("CEIS Manuel Gual", 160),
    ("CEIS Manuelita Sáenz", 200),
    ("Liceo Narciso Gonell Catia La Mar", 500),
    ("Universidad Marítima del Caribe", 500),
    ("Centro de Adiestramiento Naval Escuela de Grumetes", 400),
    ("Liceo Armando Reverón", 400),
    ("UENB 10 de Marzo", 400),
    ("Liceo Nacional Lorenzo González", 500),
    ("UEN Juan Germán Roscio", 200),
)

DISPOSAL_SITES = (
    "Av. Balneario",
    "Av. Principal Playa Grande",
    "CDT Metales",
    "Vía Alterna",
    "Parque Tecnológico Ambiental Santa Eduvigis",
    "El Ejército",
    "Atanasio 2",
    "Las 15 Letras",
    "Parque Ayacucho",
    "Los Indios",
    "Caribe Campos",
    "Charaima",
    "Carmen de Uria",
    "Punta Tanguarena",
)

HEALTH_DISTANCES = (
    ("Centro de Atención Psicofamiliar El Niño y El Mar", "hospital", 566),
    ("Hospital Materno Infantil Ana Teresa de Jesús Ponce", "hospital", 269),
    ("Dora Mercedes González", "CDI", 431),
    ("La Páez", "CDI", 580),
    ("10 de Marzo", "CDI", 669),
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def haversine_m(
    longitude_a: float,
    latitude_a: float,
    longitude_b: float,
    latitude_b: float,
) -> float:
    radius_m = 6_371_000
    phi_a = math.radians(latitude_a)
    phi_b = math.radians(latitude_b)
    delta_phi = math.radians(latitude_b - latitude_a)
    delta_lambda = math.radians(longitude_b - longitude_a)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * radius_m * math.asin(math.sqrt(value))


def candidate_crosswalk(
    site: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    nearby = sorted(
        (
            (
                haversine_m(
                    site["longitude"],
                    site["latitude"],
                    candidate["longitude"],
                    candidate["latitude"],
                ),
                candidate,
            )
            for candidate in candidates
        ),
        key=lambda item: item[0],
    )
    nearest_distance, nearest = nearby[0]
    corroborated = [
        (distance, candidate)
        for distance, candidate in nearby
        if distance <= 300
        and candidate.get("consensus") == "both_positive"
        and "temporary_shelter" in (candidate.get("assetCategories") or [])
        and candidate.get("hoursAfterEvent") is not None
    ]
    earliest = min(
        corroborated,
        key=lambda item: item[1]["hoursAfterEvent"],
        default=None,
    )
    return {
        "nearestCandidate": {
            "cellId": nearest["cellId"],
            "distanceMeters": round(nearest_distance, 1),
            "consensus": nearest.get("consensus"),
            "evidenceTier": nearest.get("evidenceTier"),
            "firstVisibleAcquisitionUtc": nearest.get("firstVisibleAcquisitionUtc"),
            "hoursAfterEvent": nearest.get("hoursAfterEvent"),
            "assetCategories": nearest.get("assetCategories") or [],
        },
        "earliestCrossModelShelterSignalWithin300m": (
            {
                "cellId": earliest[1]["cellId"],
                "distanceMeters": round(earliest[0], 1),
                "firstVisibleAcquisitionUtc": earliest[1][
                    "firstVisibleAcquisitionUtc"
                ],
                "hoursAfterEvent": earliest[1]["hoursAfterEvent"],
            }
            if earliest
            else None
        ),
        "interpretation": (
            "The MapAction product documents site use by its source date. The "
            "nearby aerial candidate is an earlier first-visible acquisition bound, "
            "not proof of the site's opening time."
        ),
    }


def estimate_range(record: dict[str, Any]) -> tuple[int | None, int | None]:
    estimate = (
        record.get("analysis", {}).get("visible_small_shelter_units_estimate")
    )
    if not isinstance(estimate, dict):
        return None, None
    minimum = estimate.get("min")
    maximum = estimate.get("max")
    return (
        int(minimum) if isinstance(minimum, (int, float)) else None,
        int(maximum) if isinstance(maximum, (int, float)) else None,
    )


def main() -> int:
    hf = {row["caseId"]: row for row in read_jsonl(ANALYSIS_DIR / "hf_router.jsonl")}
    minimax = {
        row["caseId"]: row
        for row in read_jsonl(ANALYSIS_DIR / "minimax.jsonl")
    }
    candidates = read_jsonl(PUBLIC_CANDIDATES)
    sites = []
    for definition in SITE_DEFINITIONS:
        site = dict(definition)
        site["aerialCrosscheck"] = candidate_crosswalk(site, candidates)
        sites.append(site)

    count_quality = []
    for case_id in (
        "mapaction-ma018-polideportivo",
        "mapaction-ma022-playa-grande",
        "mapaction-ma023-cesar-nieves",
        "mapaction-ma044-mare-abajo",
    ):
        hf_range = estimate_range(hf[case_id])
        minimax_range = estimate_range(minimax[case_id])
        overlap = (
            hf_range[0] is not None
            and hf_range[1] is not None
            and minimax_range[0] is not None
            and minimax_range[1] is not None
            and max(hf_range[0], minimax_range[0])
            <= min(hf_range[1], minimax_range[1])
        )
        count_quality.append(
            {
                "caseId": case_id,
                "rangesOverlap": overlap,
                "publicationDecision": "withhold-visual-unit-count",
            }
        )

    output = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "public-documentary-evidence",
        "scope": "La Guaira, Catia La Mar and Caraballeda",
        "headlineFindings": {
            "mappedResponseSites": len(sites),
            "sitesWithAnnotatedSleepingAreas": sum(
                site["sleepingEvidence"]["annotatedSleepingAreas"] > 0
                for site in sites
            ),
            "annotatedSleepingAreas": sum(
                site["sleepingEvidence"]["annotatedSleepingAreas"]
                for site in sites
            ),
            "capacityLabeledShelters": len(CAPACITY_LABELS),
            "printedCapacityPeopleTotal": sum(
                capacity for _, capacity in CAPACITY_LABELS
            ),
            "namedTemporaryWasteSites": len(DISPOSAL_SITES),
            "healthFacilitiesWithPrintedWasteDistance": len(HEALTH_DISTANCES),
        },
        "responseSites": sites,
        "shelterCapacityLabels": [
            {"name": name, "printedCapacityPeople": capacity}
            for name, capacity in CAPACITY_LABELS
        ],
        "operationalCentres": [
            {
                "name": "RDC",
                "area": "Catia La Mar / Urimare",
                "documentedAsOf": "2026-07-06",
            },
            {
                "name": "UCC / OSOCC / CICOM",
                "area": "Macuto, near IMPM UPEL",
                "documentedAsOf": "2026-07-06",
            },
            {
                "name": "2nd BoO",
                "area": "Caraballeda",
                "documentedAsOf": "2026-07-06",
            },
        ],
        "debrisManagement": {
            "documentedAsOf": "2026-07-16",
            "namedTemporaryDisposalAndSortingSites": list(DISPOSAL_SITES),
            "healthFacilityDistances": [
                {
                    "facilityName": name,
                    "facilityType": facility_type,
                    "distanceMeters": distance,
                }
                for name, facility_type, distance in HEALTH_DISTANCES
            ],
            "interpretation": (
                "The maps document temporary waste-site locations and printed "
                "distance buffers. They do not establish health impact or opening dates."
            ),
        },
        "additionalImageryInventory": {
            "sourceUrl": "https://un-spider.org/news-and-events/news/unoosa-un-spiders-disaster-response-venezuela-earthquake-june-2026-0",
            "reportedImageCountApprox": 120,
            "relevantPublishedExamples": [
                {
                    "sensor": "WorldView-2",
                    "location": "Playa Verde, La Guaira",
                    "preEventDate": "2026-06-22",
                    "postEventDate": "2026-06-25",
                    "resolutionMeters": 0.5,
                    "availability": "public derivative map; raw imagery restricted",
                },
                {
                    "sensor": "Beijing-3A1",
                    "location": "La Atlántida, Catia La Mar",
                    "postEventDate": "2026-06-26T15:04:00Z",
                    "resolutionMeters": 0.5,
                    "availability": "public comparison figure; raw imagery not linked",
                },
                {
                    "sensor": "StriX-3 SAR",
                    "location": "Venezuela response coverage",
                    "postEventDate": "2026-06-28T20:04:00Z",
                    "resolutionMeters": 0.95,
                    "availability": "public example and metadata; raw imagery not linked",
                },
            ],
            "limitation": (
                "UN-SPIDER reports a larger acquisition pool, but most raw scenes "
                "were distributed to response partners and are not publicly downloadable."
            ),
        },
        "modelQuality": {
            "hfCostEstimateUsd": 0.0077,
            "minimaxBilling": "subscription quota",
            "campUnitCountComparisons": count_quality,
            "decision": (
                "Directly printed labels are retained. Visual shelter-unit counts are "
                "withheld because provider ranges are not stable enough for publication."
            ),
        },
        "dataQualityIssues": [
            {
                "severity": "high",
                "issue": (
                    "The MA020 legend prints 2027-07-03 for several shelter layers, "
                    "which conflicts with the June 2026 event and July 6, 2026 product date."
                ),
                "handling": (
                    "Use the July 6, 2026 publication date as the safe documented-by "
                    "bound; do not silently rewrite the printed legend date."
                ),
            },
            {
                "severity": "high",
                "issue": "VLM shelter-unit estimates diverge materially across providers.",
                "handling": "Do not publish unit, tent, occupancy, or population counts from the images.",
            },
            {
                "severity": "medium",
                "issue": (
                    "MapAction products document conditions as of a date but do not "
                    "provide opening times for the mapped sites."
                ),
                "handling": (
                    "Treat site dates as latest-known bounds and aerial first-visible "
                    "dates as earlier acquisition bounds, never exact arrival times."
                ),
            },
        ],
        "sources": [
            {
                "id": "mapaction-ma020-v2",
                "label": "MapAction La Guaira key infrastructure map series",
                "url": "https://maps.mapaction.org/dataset/2026-ven-001-ma020-v2",
                "publishedAt": "2026-07-06",
            },
            *[
                {
                    "id": site["mapProductId"],
                    "label": site["name"],
                    "url": site["datasetUrl"],
                    "publishedAt": site["documentedAsOf"],
                }
                for site in SITE_DEFINITIONS
            ],
            {
                "id": "mapaction-ma055-v1",
                "label": "Temporary Waste Disposal & Sorting Centers",
                "url": "https://maps.mapaction.org/dataset/2026-ven-001-ma055-v1",
                "publishedAt": "2026-07-16",
            },
            {
                "id": "mapaction-ma056-v1",
                "label": "Impacto de los sitios de escombros en refugios y establecimientos de salud",
                "url": "https://maps.mapaction.org/dataset/2026-ven-001-ma056-v1",
                "publishedAt": "2026-07-17",
            },
            {
                "id": "un-spider-venezuela-imagery",
                "label": "UN-SPIDER Venezuela earthquake satellite imagery response",
                "url": "https://un-spider.org/news-and-events/news/unoosa-un-spiders-disaster-response-venezuela-earthquake-june-2026-0",
                "publishedAt": "2026-07-09",
            },
        ],
        "guardrails": [
            "Map symbols and annotations remain attributed documentary evidence.",
            "Aerial VLM results remain triage candidates, not official facts.",
            "First-visible dates are acquisition bounds, not actual arrival times.",
            "Raw restricted imagery is not republished or presented as public source data.",
            "A missing label or model signal never proves absence.",
        ],
    }
    PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    )
    report = [
        "# MapAction response-site evidence expansion",
        "",
        f"- Generated: `{output['generatedAt']}`",
        f"- Mapped response sites: `{len(sites)}`",
        f"- Capacity-labelled shelters: `{len(CAPACITY_LABELS)}`",
        f"- Printed capacity total: `{output['headlineFindings']['printedCapacityPeopleTotal']}`",
        f"- Named waste sites: `{len(DISPOSAL_SITES)}`",
        f"- Public output: `{PUBLIC_OUTPUT.relative_to(ROOT)}`",
        "",
        "## Publication decision",
        "",
        "Direct labels, source dates, service annotations and printed distances are",
        "retained. Visual shelter-unit counts are withheld because provider ranges",
        "diverge materially and cannot support a defensible public count.",
        "",
        "## Overlap rationale",
        "",
        "This package supplements the existing 2,283-cell Qwen/MiniMax/WALDO30",
        "analysis. It preserves the prior aerial evidence and adds separate",
        "MapAction/UN-SPIDER documentary evidence rather than reclassifying model",
        "candidates or replacing official EMS metrics.",
        "",
    ]
    (ANALYSIS_DIR / "publication_report.md").write_text("\n".join(report))
    print(json.dumps(output["headlineFindings"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
