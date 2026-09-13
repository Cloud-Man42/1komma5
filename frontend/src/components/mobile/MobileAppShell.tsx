"use client";

import { MobileBottomNav } from "@/components/mobile/MobileBottomNav";
import { MobileTopBar } from "@/components/mobile/MobileTopBar";
import { OfflineBanner } from "@/components/pwa/OfflineBanner";

export function MobileAppShell({
  children,
  freshnessLabel,
}: {
  children: React.ReactNode;
  freshnessLabel?: string | null;
}) {
  return (
    <div className="mobile-app-shell">
      <OfflineBanner />
      <MobileTopBar freshnessLabel={freshnessLabel} />
      <main className="mobile-app-main">{children}</main>
      <MobileBottomNav />
    </div>
  );
}
