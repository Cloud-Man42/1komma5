"use client";

import { usePathname } from "next/navigation";
import { MobileAppShell } from "@/components/mobile/MobileAppShell";
import { useMobileShellContext } from "@/lib/MobileShellProvider";
import { useMobileShell } from "@/lib/useMobileShell";

export function GlobalMobileShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const mobile = useMobileShell();
  const { freshnessLabel } = useMobileShellContext();

  const isExcluded =
    pathname.startsWith("/display") ||
    pathname.startsWith("/login") ||
    pathname.startsWith("/app");

  if (!mobile || isExcluded) {
    return <>{children}</>;
  }

  return <MobileAppShell freshnessLabel={freshnessLabel}>{children}</MobileAppShell>;
}
