"use client";

import { useOnlineStatus } from "@/lib/useOnlineStatus";

export function MobileOfflineGuard({
  children,
  message = "Controls disabled while offline",
}: {
  children: React.ReactNode;
  message?: string;
}) {
  const online = useOnlineStatus();
  if (online) return <>{children}</>;
  return (
    <div className="mobile-offline-guard" aria-live="polite">
      <p className="mobile-offline-guard-msg">{message}</p>
    </div>
  );
}
