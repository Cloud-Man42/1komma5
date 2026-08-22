import { useEffect, useState } from "react";
import { fetchHeartbeatConfig } from "@/lib/api";

const DEFAULT_REFRESH_SECONDS = 30;

export function useDashboardRefreshSeconds(): number {
  const [seconds, setSeconds] = useState(DEFAULT_REFRESH_SECONDS);

  useEffect(() => {
    let active = true;
    fetchHeartbeatConfig()
      .then((config) => {
        if (active) setSeconds(config.dashboard_refresh_seconds);
      })
      .catch(() => {
        if (active) setSeconds(DEFAULT_REFRESH_SECONDS);
      });
    return () => {
      active = false;
    };
  }, []);

  return seconds;
}
