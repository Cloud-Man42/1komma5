import { ReactNode } from "react";

export function Card({ title, children, className = "" }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`admin-card ${className}`.trim()}>
      {title ? <h3 className="admin-card-title">{title}</h3> : null}
      {children}
    </section>
  );
}
