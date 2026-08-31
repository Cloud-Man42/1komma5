"use client";

import Link from "next/link";
import { IconHome } from "./PiIcons";
import { piHref } from "./piSections";

export function PiHomeButton({ slug, isHome = false }: { slug: string; isHome?: boolean }) {
  return (
    <Link
      href={piHref(slug)}
      className={`pi-home-btn${isHome ? " is-active" : ""}`}
      aria-label="Hem"
      aria-current={isHome ? "page" : undefined}
    >
      <IconHome />
    </Link>
  );
}
