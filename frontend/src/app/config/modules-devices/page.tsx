import { Suspense } from "react";
import { ModulesDevicesOverview } from "@/components/modules-devices/ModulesDevicesOverview";

export default function ModulesDevicesPage() {
  return (
    <Suspense fallback={<p className="muted">Laddar…</p>}>
      <ModulesDevicesOverview />
    </Suspense>
  );
}
