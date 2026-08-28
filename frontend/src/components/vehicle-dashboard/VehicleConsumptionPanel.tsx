export function VehicleConsumptionPanel({
  bars,
  avgRenewableSharePct,
  totalEnergyKwh,
}: {
  bars: number[];
  avgRenewableSharePct: number | null;
  totalEnergyKwh: number;
}) {
  return (
    <section className="vdash-card" id="kostnad" data-testid="vehicle-consumption">
      <header className="vdash-card-header">
        <div>
          <h2>ENERGIHISTORIK</h2>
          <p className="vdash-card-sub">Senaste laddsessioner</p>
        </div>
      </header>
      <div className="vdash-consumption-head">
        <strong>{totalEnergyKwh.toFixed(1)} kWh totalt</strong>
        {avgRenewableSharePct != null ? (
          <span className="vdash-badge-green">{Math.round(avgRenewableSharePct)}% förnybar</span>
        ) : null}
      </div>
      {bars.length > 0 ? (
        <div className="vdash-bar-chart" aria-hidden="true">
          {bars.map((h, i) => (
            <span key={i} className="vdash-bar" style={{ height: `${Math.max(h, 8)}%` }} />
          ))}
        </div>
      ) : (
        <p className="vdash-muted">Ingen laddhistorik att visa ännu.</p>
      )}
    </section>
  );
}
