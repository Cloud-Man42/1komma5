import { Suspense } from "react";
import { AddDeviceWizard } from "@/components/modules-devices/AddDeviceWizard";

export default function AddDevicePage() {
  return (
    <Suspense fallback={<p className="muted">Laddar…</p>}>
      <AddDeviceWizard />
    </Suspense>
  );
}
