"use client";

import { useParams } from "next/navigation";
import { ArcticSpaPanel } from "@/components/ArcticSpaPanel";

export default function SiteSpaPage() {
  const params = useParams<{ slug: string }>();
  return (
    <>
      <h2 className="page-title">Arctic Spa</h2>
      <ArcticSpaPanel siteSlug={params.slug} />
    </>
  );
}
