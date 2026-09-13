import { ReactNode } from "react";

export function PageHeader({
  title,
  intro,
  actions,
}: {
  title: string;
  intro?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="admin-page-header">
      <div className="admin-page-header-text">
        <h1 className="admin-page-title">{title}</h1>
        {intro ? <p className="admin-page-intro muted">{intro}</p> : null}
      </div>
      {actions ? <div className="admin-page-actions">{actions}</div> : null}
    </header>
  );
}
