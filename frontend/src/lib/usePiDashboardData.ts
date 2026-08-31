"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchDisplayOverview, type DisplayOverview, type PiConnectionState } from "@/lib/displayOverview";

const POLL_MS = 4000;
const BACKOFF_MAX_MS = 30000;

export function usePiDashboardData(slug: string) {
  const [data, setData] = useState<DisplayOverview | null>(null);
  const [connection, setConnection] = useState<PiConnectionState>("RECONNECTING");
  const [error, setError] = useState<string | null>(null);
  const backoffRef = useRef(POLL_MS);
  const timerRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      const overview = await fetchDisplayOverview(slug);
      setData(overview);
      setConnection("CONNECTED");
      setError(null);
      backoffRef.current = POLL_MS;
    } catch (err) {
      setConnection((prev) => (prev === "CONNECTED" ? "RECONNECTING" : "OFFLINE"));
      setError(err instanceof Error ? err.message : "Unknown error");
      backoffRef.current = Math.min(backoffRef.current * 2, BACKOFF_MAX_MS);
    }
  }, [slug]);

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      if (cancelled) return;
      await load();
      if (!cancelled) {
        timerRef.current = window.setTimeout(tick, backoffRef.current);
      }
    };

    void tick();
    return () => {
      cancelled = true;
      if (timerRef.current != null) window.clearTimeout(timerRef.current);
    };
  }, [load]);

  return { data, connection, error, reload: load };
}
