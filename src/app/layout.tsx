import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/next";
import AnalyticsEvents from "@/components/AnalyticsEvents";
import "./globals.css";

export const metadata: Metadata = {
  title: "Crisis Damage Intelligence",
  description: "Static-first bilingual earthquake damage intelligence platform",
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
        <Analytics />
      </body>
    </html>
  );
}
