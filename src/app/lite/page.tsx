import type { Metadata } from "next";
import LiteConsole from "@/components/LiteConsole";

export const metadata: Metadata = {
  title: "Vista ligera | Respuesta Venezuela",
  description: "Vista publica ligera de zonas afectadas y descargas basicas.",
};

export default function LitePage() {
  return <LiteConsole />;
}
