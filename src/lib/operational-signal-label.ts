import type { Language, OperationalSignalFeature } from "@/components/types";

export function operationalSignalSectorLabel(
  properties: OperationalSignalFeature["properties"],
  language: Language,
) {
  const label = properties.sectorLabel ?? properties.id;
  if (language === "es") return label;
  return label
    .replace("Brechas visuales HOT/MapSwipe fuera de EMS", "HOT/MapSwipe visual gaps outside EMS")
    .replace("Puntos oficiales EMSR884", "Official EMSR884 points")
    .replace("Puntos EMSR884", "EMSR884 points")
    .replace("Daño predicho", "Predicted damage")
    .replace("Candidatos triage", "Triage candidates")
    .replace("Caraballeda Este", "Caraballeda East")
    .replace("Catia La Mar Este", "Catia La Mar East")
    .replace("La Guaira Este", "La Guaira East")
    .replace("Zona predicción externa", "External prediction zone")
    .replace("Zona triage externo", "External triage zone")
    .replace("Zona MONIT01", "MONIT01 zone")
    .replace("Zona de impacto", "Impact zone");
}
