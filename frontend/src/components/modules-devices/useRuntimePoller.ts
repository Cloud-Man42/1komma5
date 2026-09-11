"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const TERMINAL = new Set(["running", "stopped", "blocked", "failed", "unknown"]);
const TRANSITION = new Set(["starting", "stopping"]);

type PollTarget = {
  runtime_status: string;
};

type Options<T extends PollTarget> = {
  enabled: boolean;
  fetchState: () => Promise<T>;
  intervalMs?: number;
  timeoutMs?: number;
  onUpdate?: (state: T) => void;
};

export function useRuntimePoller<T extends PollTarget>({
  enabled,
  fetchState,
  intervalMs = 1500,
  timeoutMs = 30000,
  onUpdate,
}: Options<T>) {
  const [polling, setPolling] = useState(false);
  const timerRef = useRef<number | null>(null);
  const startedRef = useRef<number | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setPolling(false);
    startedRef.current = null;
  }, []);

  const pollOnce = useCallback(async () => {
    const state = await fetchState();
    onUpdate?.(state);
    const status = state.runtime_status.toLowerCase();
    if (TERMINAL.has(status) && !TRANSITION.has(status)) {
      stop();
    }
    if (startedRef.current !== null && Date.now() - startedRef.current > timeoutMs) {
      stop();
    }
    return state;
  }, [fetchState, onUpdate, stop, timeoutMs]);

  useEffect(() => {
    if (!enabled) {
      stop();
      return;
    }
    setPolling(true);
    startedRef.current = Date.now();
    void pollOnce();
    timerRef.current = window.setInterval(() => {
      void pollOnce();
    }, intervalMs);
    return stop;
  }, [enabled, intervalMs, pollOnce, stop]);

  return { polling, stop, pollOnce };
}
