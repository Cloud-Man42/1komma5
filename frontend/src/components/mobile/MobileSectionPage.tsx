"use client";

import Link from "next/link";

export function MobileSectionPage({
  title,
  subtitle,
  backHref = "/app",
  children,
}: {
  title: string;
  subtitle?: string;
  backHref?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mobile-section-page">
      <div className="mobile-section-header">
        <Link href={backHref} className="mobile-section-back">
          ← Back
        </Link>
        <h1 className="mobile-section-title">{title}</h1>
        {subtitle ? <p className="muted mobile-section-subtitle">{subtitle}</p> : null}
      </div>
      {children}
    </div>
  );
}
