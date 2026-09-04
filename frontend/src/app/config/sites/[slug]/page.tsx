"use client";

import { use } from "react";
import { SiteConfigDetail } from "@/components/config/sites/SiteConfigDetail";

export default function ConfigSiteDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  return <SiteConfigDetail slug={slug} />;
}
