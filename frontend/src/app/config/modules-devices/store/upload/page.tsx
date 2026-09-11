import { Suspense } from "react";
import { PackageUploadWizard } from "@/components/modules-devices/PackageUploadWizard";

export default function ModuleStoreUploadPage() {
  return (
    <Suspense fallback={<p className="muted">Laddar…</p>}>
      <PackageUploadWizard />
    </Suspense>
  );
}
