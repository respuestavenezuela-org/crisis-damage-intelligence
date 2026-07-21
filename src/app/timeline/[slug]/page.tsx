import type { Metadata } from "next";
import { notFound } from "next/navigation";
import TimelineExplorer from "@/components/reconstruction/TimelineExplorer";
import {
  getReconstruction,
  getReconstructionSlugs,
  reconstructionCatalog,
} from "@/lib/reconstruction";

export const dynamicParams = false;

export function generateStaticParams() {
  return getReconstructionSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const entry = reconstructionCatalog.entries.find((candidate) => candidate.slug === slug);
  if (!entry) return {};
  return {
    title: `${entry.geography.es} | Lo que pasó después`,
    description: entry.description.es,
    alternates: {
      canonical: `/timeline/${slug}`,
    },
    openGraph: {
      title: `Lo que pasó después: ${entry.geography.es}`,
      description: entry.description.es,
      type: "article",
      locale: "es_VE",
      alternateLocale: "en_US",
      url: `/timeline/${slug}`,
    },
  };
}

export default async function ReconstructionPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const data = getReconstruction(slug);
  if (!data) notFound();
  return (
    <TimelineExplorer
      data={data}
      catalog={reconstructionCatalog}
      activeSlug={slug}
    />
  );
}
