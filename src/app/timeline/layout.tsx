import { IBM_Plex_Mono, Newsreader } from "next/font/google";
import type { ReactNode } from "react";
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

export default function TimelineLayout({ children }: { children: ReactNode }) {
  return (
    <div className={`${newsreader.variable} ${ibmPlexMono.variable} ${styles.fontScope}`}>
      {children}
    </div>
  );
}
