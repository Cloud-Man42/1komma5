"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { IconChevron } from "./PiIcons";

export function PiTouchCard({
  href,
  className = "",
  ariaLabel,
  children,
}: {
  href: string;
  className?: string;
  ariaLabel: string;
  children: ReactNode;
}) {
  return (
    <Link href={href} className={`pi-touch ${className}`.trim()} aria-label={ariaLabel}>
      {children}
      <IconChevron className="pi-touch-chevron" />
    </Link>
  );
}
