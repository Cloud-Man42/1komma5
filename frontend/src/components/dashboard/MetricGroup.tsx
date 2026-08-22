import { ReactNode } from "react";

export function MetricGroup({ children }: { children: ReactNode }) {
  return <div className="metric-group">{children}</div>;
}
