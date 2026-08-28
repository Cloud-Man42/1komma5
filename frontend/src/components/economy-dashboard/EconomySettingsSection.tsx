"use client";

import Link from "next/link";
import { formatEconomyKr, resolveSiteInvestmentSek } from "./economyDashboardHelpers";

export function EconomySettingsSection({ siteSlug }: { siteSlug: string }) {
  return (
    <section className="edash-section" data-testid="economy-settings-section">
      <header className="edash-section-head">
        <h2>Inställningar</h2>
        <p>Priser, kompensation och ekonomiska antaganden.</p>
      </header>
      <div className="edash-settings-cards">
        <article className="edash-panel">
          <h3>Anläggningspriser</h3>
          <p className="edash-muted">
            Konfigurera inköpspris, exportersättning och nätavgifter för {siteSlug}.
          </p>
          <Link href="/config" className="edash-outline-btn">
            Öppna inställningar
          </Link>
        </article>
        <article className="edash-panel">
          <h3>Budget &amp; investering</h3>
          <p className="edash-muted">
            Total investering för {siteSlug}: {formatEconomyKr(resolveSiteInvestmentSek(siteSlug))}.
            Månadskostnad och investering används för budgetmätare och avkastningsberäkning.
          </p>
        </article>
      </div>
    </section>
  );
}
