import type { Metadata } from "next";
import EvidenceExplorer from "@/components/evidence/EvidenceExplorer";

export const metadata: Metadata = {
  title: "Atlas de evidencia aérea | Respuesta Venezuela",
  description:
    "Explora las 399 celdas candidatas, 500 pares de evidencia y diez casos revisados del piloto aéreo de La Guaira, Caraballeda y Catia La Mar.",
  alternates: {
    canonical: "/evidence/la-guaira",
  },
  openGraph: {
    title: "Atlas de evidencia aérea",
    description:
      "Mapa, cronología e imágenes nativas de las 399 candidatas del piloto aéreo completo.",
    type: "website",
    locale: "es_VE",
    alternateLocale: "en_US",
    url: "/evidence/la-guaira",
  },
};

export default function LaGuairaEvidencePage() {
  return <EvidenceExplorer />;
}
