import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import AnalyticsEvents from "@/components/AnalyticsEvents";
import OpenPanelAnalytics from "@/components/OpenPanelAnalytics";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://respuestavenezuela.org"),
  title: "Crisis Damage Intelligence",
  description: "Static-first bilingual earthquake damage intelligence platform",
  alternates: {
    canonical: "/",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
        <AnalyticsEvents />
        <OpenPanelAnalytics />
        <Analytics />
      </body>
    </html>
  );
}
