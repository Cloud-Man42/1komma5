"use client";

import Link from "next/link";
import { APP_ACRONYM } from "@/lib/brand";
import { UserMenu } from "@/components/UserMenu";
import { useAuth } from "@/lib/authContext";
import { MobileSiteSelectorTrigger } from "@/components/mobile/MobileSiteSelectorSheet";

export function MobileTopBar({ freshnessLabel }: { freshnessLabel?: string | null }) {
  const { user, loading } = useAuth();
  const userAuthEnabled = process.env.NEXT_PUBLIC_EMIC_USER_AUTH_ENABLED === "true";

  return (
    <header className="mobile-topbar">
      <div className="mobile-topbar-row">
        <Link href="/app" className="mobile-topbar-brand">
          {APP_ACRONYM}
        </Link>
        <div className="mobile-topbar-actions">
          {freshnessLabel ? (
            <span className={`mobile-freshness${freshnessLabel.startsWith("Stale") ? " mobile-freshness-stale" : ""}`}>
              {freshnessLabel}
            </span>
          ) : null}
          {userAuthEnabled && !loading && user ? <UserMenu compact /> : null}
        </div>
      </div>
      <MobileSiteSelectorTrigger />
    </header>
  );
}
