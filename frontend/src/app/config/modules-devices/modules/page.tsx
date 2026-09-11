import { Suspense } from "react";
import { ModulesDevicesOverview } from "@/components/modules-devices/ModulesDevicesOverview";

export default function ModulesListPage() {
  return (
    <Suspense fallback={<p className="muted">Laddar…</p>}>
      <ModulesDevicesOverview />
    </Suspense>
  );
}
