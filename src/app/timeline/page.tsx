import type { Metadata } from "next";
import TimelineExplorer from "@/components/reconstruction/TimelineExplorer";
import {
  getDefaultReconstruction,
  reconstructionCatalog,
} from "@/lib/reconstruction";

export const metadata: Metadata = {
  title: "Lo que pasó después | Respuesta Venezuela",
  description:
    "Reconstrucción pública y verificable de los terremotos del 24 de junio de 2026 y la respuesta en La Guaira, Caraballeda y Catia La Mar.",
  alternates: {
    canonical: "/timeline",
  },
  openGraph: {
    title: "Lo que pasó después",
    description:
      "Una cronología de la respuesta basada en imagen, reportes operativos y fuentes enlazadas.",
    type: "article",
    locale: "es_VE",
    alternateLocale: "en_US",
    url: "/timeline",
  },
};

export default function TimelinePage() {
  return (
    <TimelineExplorer
      data={getDefaultReconstruction()}
      catalog={reconstructionCatalog}
      activeSlug={reconstructionCatalog.defaultSlug}
    />
  );
}
