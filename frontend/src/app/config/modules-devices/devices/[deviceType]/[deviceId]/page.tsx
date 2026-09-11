import { Suspense } from "react";
import { DeviceDetailPanel } from "@/components/modules-devices/DeviceDetailPanel";

type Props = {
  params: Promise<{ deviceType: string; deviceId: string }>;
  searchParams: Promise<{ site?: string }>;
};

export default async function DeviceDetailPage({ params, searchParams }: Props) {
  const { deviceType, deviceId } = await params;
  const { site = "akarp" } = await searchParams;
  return (
    <Suspense fallback={<p className="muted">Laddar…</p>}>
      <DeviceDetailPanel siteSlug={site} deviceType={deviceType} deviceId={Number(deviceId)} />
    </Suspense>
  );
}
