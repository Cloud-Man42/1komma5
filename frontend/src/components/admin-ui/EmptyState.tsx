import { ReactNode } from "react";

export function EmptyState({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="admin-empty-state">
      <h3 className="admin-empty-title">{title}</h3>
      {text ? <p className="admin-empty-text muted">{text}</p> : null}
      {action ? <div className="admin-empty-action">{action}</div> : null}
    </div>
  );
}
