"use client";

import { ReactNode, useEffect } from "react";

export function SpaDrawer({
  title,
  open,
  onClose,
  children,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="sdash-drawer-backdrop" onClick={onClose} role="presentation">
      <section
        className="sdash-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="sdash-drawer-head">
          <h2>{title}</h2>
          <button type="button" className="sdash-drawer-close" onClick={onClose}>
            Stäng
          </button>
        </header>
        <div className="sdash-drawer-body">{children}</div>
      </section>
    </div>
  );
}
