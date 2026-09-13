"use client";

import { useCallback, useEffect, useState } from "react";
import { useOnlineStatus } from "@/lib/useOnlineStatus";

export type ServerReachability = "checking" | "reachable" | "unreachable" | "offline";

async function probeHealth(): Promise<boolean> {
  try {
    const res = await fetch("/health", { cache: "no-store", credentials: "omit" });
    return res.ok;
  } catch {
    return false;
  }
}

export function useServerReachability(): {
  status: ServerReachability;
  retry: () => void;
} {
  const online = useOnlineStatus();
  const [status, setStatus] = useState<ServerReachability>("checking");

  const check = useCallback(async () => {
    if (!online) {
      setStatus("offline");
      return;
    }
    setStatus("checking");
    const reachable = await probeHealth();
    setStatus(reachable ? "reachable" : "unreachable");
  }, [online]);

  useEffect(() => {
    void check();
  }, [check]);

  useEffect(() => {
    const onOnline = () => {
      void check();
    };
    window.addEventListener("online", onOnline);
    return () => window.removeEventListener("online", onOnline);
  }, [check]);

  return { status, retry: check };
}
