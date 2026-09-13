"use client";

import { useOnlineStatus } from "@/lib/useOnlineStatus";

export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <div className="mobile-offline-banner" role="status">
      <strong>Offline</strong>
      <span>Live data unavailable · Controls disabled</span>
    </div>
  );
}
