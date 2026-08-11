import type { Metadata } from "next";
import ColombiaMapExperience from "@/components/colombia/ColombiaMapExperience";
import type {
  ColombiaIncident,
  ColombiaMappingSnapshot,
} from "@/components/colombia/types";
import incidentData from "../../../public/data/incidents/colombia-2026-08-10-san-jose-del-palmar.json";
import mappingData from "../../../public/data/incidents/colombia-2026-08-10-emsr916-map.json";

export const metadata: Metadata = {
  title: "Mapa operativo del sismo en Colombia | Respuesta",
  description:
    "Mapa bilingüe del sismo M7.4 en Colombia con el epicentro, las áreas oficiales Copernicus EMSR916 y el estado verificable de imágenes antes/después.",
  alternates: {
    canonical: "/colombia",
  },
  openGraph: {
    type: "website",
    url: "/colombia",
    title: "Mapa operativo del sismo en Colombia",
    description:
      "Epicentro, áreas oficiales de cartografía y estado de adquisición de imágenes Copernicus EMSR916.",
  },
};

export default function ColombiaPage() {
  return (
    <ColombiaMapExperience
      incident={incidentData as ColombiaIncident}
      mapping={mappingData as ColombiaMappingSnapshot}
    />
  );
}
