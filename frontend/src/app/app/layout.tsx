"use client";

import { MobileAppShell } from "@/components/mobile/MobileAppShell";
import { useMobileShellContext } from "@/lib/MobileShellProvider";

export default function MobileAppLayout({ children }: { children: React.ReactNode }) {
  const { freshnessLabel } = useMobileShellContext();
  return <MobileAppShell freshnessLabel={freshnessLabel}>{children}</MobileAppShell>;
}
