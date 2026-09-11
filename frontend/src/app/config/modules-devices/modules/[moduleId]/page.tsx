import { Suspense } from "react";
import { ModuleDetailPanel } from "@/components/modules-devices/ModuleDetailPanel";

type Props = {
  params: Promise<{ moduleId: string }>;
  searchParams: Promise<{ site?: string }>;
};

export default async function ModuleDetailPage({ params, searchParams }: Props) {
  const { moduleId } = await params;
  const { site = "akarp" } = await searchParams;
  return (
    <Suspense fallback={<p className="muted">Laddar…</p>}>
      <ModuleDetailPanel siteSlug={site} moduleId={decodeURIComponent(moduleId)} />
    </Suspense>
  );
}
