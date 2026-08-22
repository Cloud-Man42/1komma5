import { ReactNode } from "react";

export function DashboardSection({
  title,
  subtitle,
  action,
  children,
  className,
}: {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`dashboard-section ${className ?? ""}`.trim()}>
      <div className="dashboard-section-header">
        <div>
          <h2 className="dashboard-section-title">{title}</h2>
          {subtitle && <p className="dashboard-section-subtitle">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
