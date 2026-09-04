"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  buildDisplayOverviewStreamUrl,
  fetchDisplayOverview,
  type DisplayOverview,
  type PiConnectionState,
} from "@/lib/displayOverview";
import {
  derivePiConnectionState,
  formatLastUpdated,
  loadPiLastKnownGood,
  savePiLastKnownGood,
} from "@/lib/piDashboardStorage";

const POLL_MS = 4000;
const BACKOFF_MAX_MS = 30000;

export function usePiDashboardData(slug: string) {
  const [data, setData] = useState<DisplayOverview | null>(() => loadPiLastKnownGood(slug));
  const [connection, setConnection] = useState<PiConnectionState>("RECONNECTING");
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(() =>
    formatLastUpdated(loadPiLastKnownGood(slug)),
  );
  const backoffRef = useRef(POLL_MS);
  const timerRef = useRef<number | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const usingPollRef = useRef(false);

  const applyOverview = useCallback(
    (overview: DisplayOverview, fromFailure = false) => {
      setData(overview);
      savePiLastKnownGood(slug, overview);
      setConnection(derivePiConnectionState(overview, fromFailure));
      setLastUpdated(formatLastUpdated(overview));
      setError(null);
      backoffRef.current = POLL_MS;
    },
    [slug],
  );

  const handleFailure = useCallback(
    (err: unknown, cached: DisplayOverview | null) => {
      const lkg = cached ?? loadPiLastKnownGood(slug);
      if (lkg) {
        setData(lkg);
        setConnection(derivePiConnectionState(lkg, true));
        setLastUpdated(formatLastUpdated(lkg));
      } else {
        setConnection("OFFLINE");
      }
      setError(err instanceof Error ? err.message : "Unknown error");
      backoffRef.current = Math.min(backoffRef.current * 2, BACKOFF_MAX_MS);
    },
    [slug],
  );

  const load = useCallback(async () => {
    try {
      const overview = await fetchDisplayOverview(slug);
      applyOverview(overview, false);
    } catch (err) {
      handleFailure(err, loadPiLastKnownGood(slug));
    }
  }, [slug, applyOverview, handleFailure]);

  const startPolling = useCallback(() => {
    if (usingPollRef.current) return;
    usingPollRef.current = true;
    eventSourceRef.current?.close();
    eventSourceRef.current = null;

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

  useEffect(() => {
    let stopPoll: (() => void) | undefined;
    let cancelled = false;

    void load();

    if (typeof EventSource !== "undefined") {
      const source = new EventSource(buildDisplayOverviewStreamUrl(slug), { withCredentials: true });
      eventSourceRef.current = source;
      source.onmessage = (event) => {
        try {
          const overview = JSON.parse(event.data) as DisplayOverview;
          applyOverview(overview, false);
        } catch (err) {
          handleFailure(err, loadPiLastKnownGood(slug));
        }
      };
      source.onerror = () => {
        source.close();
        eventSourceRef.current = null;
        if (!cancelled) stopPoll = startPolling();
      };
    } else {
      stopPoll = startPolling();
    }

    return () => {
      cancelled = true;
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      stopPoll?.();
      if (timerRef.current != null) window.clearTimeout(timerRef.current);
    };
  }, [slug, load, applyOverview, handleFailure, startPolling]);

  return { data, connection, error, lastUpdated, reload: load };
}
