import type { Metadata } from "next";
import { IBM_Plex_Mono, Newsreader } from "next/font/google";
import TimelineExplorer from "@/components/reconstruction/TimelineExplorer";
import type { ReconstructionData } from "@/components/reconstruction/types";
import reconstruction from "../../../public/data/reconstruction/la-guaira-timeline.json";
import styles from "@/components/reconstruction/timeline.module.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-reconstruction-serif",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-reconstruction-mono",
});

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
    <div className={`${newsreader.variable} ${ibmPlexMono.variable} ${styles.fontScope}`}>
      <TimelineExplorer data={reconstruction as ReconstructionData} />
    </div>
  );
}
