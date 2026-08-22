import { ReactNode } from "react";

export function AlertBanner({ children }: { children: ReactNode }) {
  return (
    <div className="alert-banner" role="alert">
      <p className="alert-banner-title">Kräver åtgärd</p>
      {children}
    </div>
  );
}

export function AlertBannerList({ alerts }: { alerts: string[] }) {
  if (alerts.length === 0) return null;
  return (
    <AlertBanner>
      {alerts.map((alert) => (
        <p key={alert} className="alert-banner-item">
          {alert}
        </p>
      ))}
    </AlertBanner>
  );
}
