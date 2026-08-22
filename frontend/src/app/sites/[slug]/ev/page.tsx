"use client";

import { useParams } from "next/navigation";
import { EvChargerPanel } from "@/components/EvChargerPanel";

export default function SiteEvPage() {
  const params = useParams<{ slug: string }>();
  return (
    <>
      <h2 className="page-title">Laddbox</h2>
      <EvChargerPanel siteSlug={params.slug} />
    </>
  );
}
