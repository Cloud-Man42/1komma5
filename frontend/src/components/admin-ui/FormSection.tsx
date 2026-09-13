import { ReactNode } from "react";

export function FormSection({ title, intro, children }: { title: string; intro?: string; children: ReactNode }) {
  return (
    <section className="admin-form-section">
      <header className="admin-form-section-header">
        <h2 className="admin-form-section-title">{title}</h2>
        {intro ? <p className="admin-form-section-intro muted">{intro}</p> : null}
      </header>
      <div className="admin-form-section-body">{children}</div>
    </section>
  );
}
