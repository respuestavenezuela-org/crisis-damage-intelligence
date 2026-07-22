import { IBM_Plex_Mono, Newsreader } from "next/font/google";
import type { ReactNode } from "react";
import styles from "@/components/evidence/evidence-explorer.module.css";

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-evidence-serif",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-evidence-mono",
});

export default function EvidenceLayout({ children }: { children: ReactNode }) {
  return (
    <div className={`${newsreader.variable} ${ibmPlexMono.variable} ${styles.fontScope}`}>
      {children}
    </div>
  );
}
