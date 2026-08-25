"use client";

import { useEffect, useMemo, useState } from "react";
import {
  FinancialStat,
  FinancialStatsResponse,
  PeakPeriod,
  fetchFinancialStats,
} from "@/lib/api";
import { formatSekAmount, formatSekDecimal, formatSekSigned } from "@/lib/prices";
import { InfoTooltip } from "@/components/InfoTooltip";

interface FinancialStatsViewProps {
  siteSlug: string;
}

const PERIOD_LABELS: Record<PeakPeriod, string> = {
  day: "Dagar",
  month: "Månader",
  year: "År",
};

type EconomicResultTone = "positive" | "negative" | "neutral";

interface EconomicResultCopy {
  amountLabel: string;
  statusLabel: string;
  detailLabel: string;
  tone: EconomicResultTone;
  className: string;
}

export function describeEconomicResult(economicResultSek: number): EconomicResultCopy {
  const absLabel = formatSekDecimal(Math.abs(economicResultSek));

  if (Math.abs(economicResultSek) < 0.005) {
    return {
      amountLabel: "0,00 kr",
      statusLabel: "Besparingar och kostnader tar ut varandra",
      detailLabel: "Besparing och försäljning minus kostnaden för köpt el",
      tone: "neutral",
      className: "finance-card finance-result finance-result-neutral",
    };
  }

  if (economicResultSek > 0) {
    return {
      amountLabel: formatSekSigned(economicResultSek),
      statusLabel: `Du ligger ${absLabel} plus`,
      detailLabel: "Besparing och försäljning minus kostnaden för köpt el",
      tone: "positive",
      className: "finance-card finance-result finance-result-positive",
    };
  }

  return {
    amountLabel: formatSekSigned(economicResultSek),
    statusLabel: `Din energikostnad efter besparingar är ${absLabel}`,
    detailLabel: "Besparing och försäljning minus kostnaden för köpt el",
    tone: "negative",
    className: "finance-card finance-result finance-result-negative",
  };
}

export function buildFinanceSummarySentence(
  benefitSek: number,
  importCostSek: number,
  economicResultSek: number,
): string {
  const benefitLabel = formatSekDecimal(benefitSek);
  const importLabel = formatSekDecimal(importCostSek);

  if (Math.abs(economicResultSek) < 0.005) {
    return `Du har sparat och tjänat ${benefitLabel} på sol, batteri och såld el. Under samma period har du köpt el för ${importLabel}. Besparingar och kostnader tar ut varandra.`;
  }

  if (economicResultSek > 0) {
    return `Du har sparat och tjänat ${benefitLabel} på sol, batteri och såld el. Under samma period har du köpt el för ${importLabel}. Det ger ett ekonomiskt resultat på ${formatSekSigned(economicResultSek)}.`;
  }

  return `Du har sparat och tjänat ${benefitLabel} på sol, batteri och såld el. Under samma period har du köpt el för ${importLabel}. Din energikostnad efter besparingar är ${formatSekDecimal(Math.abs(economicResultSek))}.`;
}

function formatPeriod(value: string, period: PeakPeriod): string {
  if (period === "year") return value;
  const [year, month, day] = value.split("-").map(Number);
  return new Intl.DateTimeFormat("sv-SE", {
    year: "numeric",
    month: period === "month" ? "long" : "short",
    ...(period === "day" ? { day: "numeric" } : {}),
  }).format(new Date(year, month - 1, day ?? 1));
}

function formatKwh(value: number): string {
  return `${value.toLocaleString("sv-SE", { maximumFractionDigits: 1 })} kWh`;
}

interface FinanceCardProps {
  label: string;
  amount: number;
  subtitle: string;
  tooltip?: string;
  className?: string;
}

function FinanceCard({ label, amount, subtitle, tooltip, className = "finance-card" }: FinanceCardProps) {
  return (
    <div className={className}>
      {tooltip ? (
        <InfoTooltip label={label} text={tooltip} />
      ) : (
        <dt className="finance-card-label">{label}</dt>
      )}
      <dd className="finance-card-amount">{formatSekDecimal(amount)}</dd>
      <span className="finance-card-subtitle">{subtitle}</span>
    </div>
  );
}

export function FinancialStatsView({ siteSlug }: FinancialStatsViewProps) {
  const [period, setPeriod] = useState<PeakPeriod>("day");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [annualResponse, setAnnualResponse] = useState<FinancialStatsResponse | null>(null);
  const [response, setResponse] = useState<FinancialStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [annualLoading, setAnnualLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [annualError, setAnnualError] = useState<string | null>(null);

  const availableYears = useMemo(
    () =>
      (annualResponse?.stats ?? [])
        .map((stat) => Number(stat.period_start))
        .filter(Number.isFinite)
        .sort((a, b) => b - a),
    [annualResponse],
  );

  useEffect(() => {
    let active = true;
    fetchFinancialStats(siteSlug, "year")
      .then((result) => {
        if (!active) return;
        setAnnualResponse(result);
        setAnnualError(null);
        const years = result.stats.map((stat) => Number(stat.period_start)).filter(Number.isFinite);
        if (years.length > 0) setSelectedYear(Math.max(...years));
      })
      .catch((reason) => {
        if (active) {
          setAnnualError(
            reason instanceof Error ? reason.message : "Kunde inte läsa ekonomisk statistik.",
          );
        }
      })
      .finally(() => {
        if (active) setAnnualLoading(false);
      });
    return () => {
      active = false;
    };
  }, [siteSlug]);

  useEffect(() => {
    if (period === "year") {
      setResponse(annualResponse);
      setLoading(annualLoading);
      setError(annualError);
      return;
    }
    let active = true;
    setLoading(true);
    fetchFinancialStats(siteSlug, period, selectedYear)
      .then((result) => {
        if (!active) return;
        setResponse(result);
        setError(null);
      })
      .catch((reason) => {
        if (!active) return;
        setResponse(null);
        setError(
          reason instanceof Error ? reason.message : "Kunde inte läsa ekonomisk statistik.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [annualError, annualLoading, annualResponse, period, selectedYear, siteSlug]);

  const stats = response?.stats ?? [];
  const totals = useMemo(
    () =>
      stats.reduce(
        (sum, stat) => ({
          solar: sum.solar + stat.solar_savings_sek,
          battery: sum.battery + stat.battery_savings_sek,
          export: sum.export + stat.export_revenue_sek,
          import: sum.import + stat.grid_import_cost_sek,
        }),
        { solar: 0, battery: 0, export: 0, import: 0 },
      ),
    [stats],
  );
  const totalBenefit = totals.solar + totals.battery + totals.export;
  const economicResult = totalBenefit - totals.import;
  const economicResultCopy = describeEconomicResult(economicResult);
  const summarySentence = buildFinanceSummarySentence(
    totalBenefit,
    totals.import,
    economicResult,
  );
  const valuedEnergy = stats.reduce(
    (sum, stat) =>
      sum +
      stat.solar_self_consumed_kwh +
      stat.battery_self_consumed_kwh +
      stat.imported_kwh,
    0,
  );
  const pricedFraction =
    valuedEnergy > 0
      ? stats.reduce(
          (sum, stat) =>
            sum +
            stat.market_priced_fraction *
              (stat.solar_self_consumed_kwh +
                stat.battery_self_consumed_kwh +
                stat.imported_kwh),
          0,
        ) / valuedEnergy
      : 0;

  return (
    <section className="peaks-section finance-section" aria-labelledby="finance-title">
      <div className="peaks-header">
        <div>
          <h3 id="finance-title" className="section-title">Ekonomisk nytta</h3>
          <p className="muted peaks-intro">
            Hur mycket du har sparat, tjänat och betalat för el under vald period.
          </p>
        </div>
        {period !== "year" && (
          <label className="peaks-year">
            <span>År</span>
            <select
              aria-label="Välj statistikår"
              value={selectedYear}
              onChange={(event) => setSelectedYear(Number(event.target.value))}
            >
              {(availableYears.length > 0 ? availableYears : [selectedYear]).map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="peaks-tabs" role="tablist" aria-label="Ekonomisk tidsperiod">
        {(Object.keys(PERIOD_LABELS) as PeakPeriod[]).map((value) => (
          <button
            key={value}
            type="button"
            role="tab"
            aria-selected={period === value}
            className={period === value ? "peaks-tab peaks-tab-active" : "peaks-tab"}
            onClick={() => setPeriod(value)}
          >
            {PERIOD_LABELS[value]}
          </button>
        ))}
      </div>

      {!loading && !error && stats.length > 0 && (
        <>
          <dl className="finance-summary">
            <FinanceCard
              label="Solen har sparat"
              amount={totals.solar}
              subtitle="El du sluppit köpa tack vare solel"
              tooltip="Beräknad kostnad för el som du inte behövde köpa eftersom huset använde egenproducerad solel."
            />
            <FinanceCard
              label="Batteriet har sparat"
              amount={totals.battery}
              subtitle="Besparing genom att använda lagrad energi vid bättre tidpunkter"
              tooltip="Beräknad ekonomisk nytta från energi som lagrats och använts vid en mer fördelaktig tidpunkt."
            />
            <FinanceCard
              label="Du har tjänat på såld el"
              amount={totals.export}
              subtitle="Intäkt från el som skickats ut på nätet"
            />
            <FinanceCard
              label="El du faktiskt köpt"
              amount={totals.import}
              subtitle="Din beräknade kostnad för el köpt från nätet"
              tooltip="Beräknad kostnad för den el som hämtats från elnätet under vald period."
              className="finance-card finance-card-cost"
            />
            <FinanceCard
              label="Sol + batteri + försäljning"
              amount={totalBenefit}
              subtitle="Din totala besparing och intäkt"
              className="finance-card finance-card-total"
            />
            <div className={economicResultCopy.className}>
              <InfoTooltip
                label="Ekonomiskt resultat"
                text="Din totala besparing och försäljningsintäkt minus kostnaden för köpt el."
              />
              <dd className="finance-card-amount">{economicResultCopy.amountLabel}</dd>
              <strong className="finance-result-status">{economicResultCopy.statusLabel}</strong>
              <span className="finance-card-subtitle">{economicResultCopy.detailLabel}</span>
              <span className="finance-result-formula">
                {formatSekDecimal(totalBenefit)} − {formatSekDecimal(totals.import)} ={" "}
                {economicResultCopy.amountLabel}
              </span>
            </div>
          </dl>
          <p className="finance-summary-sentence">{summarySentence}</p>
          <p className="muted finance-method">
            Heartbeat-timpris används för {(pricedFraction * 100).toFixed(0)}% av den värderade
            egenanvändningen. Övrigt använder reservpriset{" "}
            {response?.fallback_purchase_price_sek_kwh.toFixed(2)} kr/kWh. Såld el värderas till{" "}
            {response?.export_compensation_sek_kwh.toFixed(2)} kr/kWh.
          </p>
        </>
      )}

      {loading ? (
        <p className="muted">Beräknar ekonomisk statistik…</p>
      ) : error ? (
        <p className="form-error" role="alert">{error}</p>
      ) : stats.length === 0 ? (
        <p className="muted">Det finns inte tillräckligt med mätdata för perioden.</p>
      ) : (
        <div className="peaks-table-wrap">
          <table className="peaks-table finance-table">
            <thead>
              <tr>
                <th scope="col">{period === "day" ? "Datum" : period === "month" ? "Månad" : "År"}</th>
                <th scope="col">Solel använd</th>
                <th scope="col">Besparing sol</th>
                <th scope="col">Batteri använt</th>
                <th scope="col">Besparing batteri</th>
                <th scope="col">Såld el</th>
                <th scope="col">Intäkt såld el</th>
                <th scope="col">Köpt el</th>
                <th scope="col">Kostnad köpt el</th>
              </tr>
            </thead>
            <tbody>
              {[...stats].reverse().map((stat: FinancialStat) => (
                <tr key={stat.period_start}>
                  <th scope="row">{formatPeriod(stat.period_start, period)}</th>
                  <td>{formatKwh(stat.solar_self_consumed_kwh)}</td>
                  <td>{formatSekAmount(stat.solar_savings_sek).label}</td>
                  <td>{formatKwh(stat.battery_self_consumed_kwh)}</td>
                  <td>{formatSekAmount(stat.battery_savings_sek).label}</td>
                  <td>{formatKwh(stat.exported_kwh)}</td>
                  <td>{formatSekAmount(stat.export_revenue_sek).label}</td>
                  <td>{formatKwh(stat.imported_kwh)}</td>
                  <td>{formatSekAmount(stat.grid_import_cost_sek).label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
