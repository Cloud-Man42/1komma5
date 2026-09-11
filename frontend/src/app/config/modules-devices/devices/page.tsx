import { Suspense } from "react";
import { DeviceListPanel } from "@/components/modules-devices/DeviceListPanel";

export default function DevicesPage() {
  return (
    <Suspense fallback={<p className="muted">Laddar…</p>}>
      <DeviceListPanel />
    </Suspense>
  );
}
