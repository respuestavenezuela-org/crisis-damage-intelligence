import type {
  ReconstructionCatalog,
  ReconstructionData,
} from "@/components/reconstruction/types";
import catalogJson from "../../public/data/reconstruction/catalog.json";
import laGuairaJson from "../../public/data/reconstruction/la-guaira-timeline.json";
import moronJson from "../../public/data/reconstruction/moron-timeline.json";

export const reconstructionCatalog = catalogJson as unknown as ReconstructionCatalog;

const reconstructions: Record<string, ReconstructionData> = {
  "la-guaira": laGuairaJson as unknown as ReconstructionData,
  moron: moronJson as unknown as ReconstructionData,
};

export function getReconstruction(slug: string) {
  return reconstructions[slug];
}

export function getDefaultReconstruction() {
  return getReconstruction(reconstructionCatalog.defaultSlug);
}

export function getReconstructionSlugs() {
  return reconstructionCatalog.entries
    .filter((entry) => entry.status === "published")
    .map((entry) => entry.slug);
}
