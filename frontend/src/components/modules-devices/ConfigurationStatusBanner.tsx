"use client";

type Props = {
  restartRequired: string;
  configurationActive?: boolean;
  configurationStatus?: string;
  effectivelyConfigured?: boolean;
  onApply?: () => void;
  applyBusy?: boolean;
  applyError?: string | null;
};

const STATUS_LABELS: Record<string, string> = {
  active: "Konfiguration aktiv",
  restart_required: "Omstart krävs innan ändringar blir aktiva",
  incomplete: "Konfiguration ofullständig",
  heartbeat_credentials_missing: "Heartbeat-kontouppgifter saknas",
  apply_failed: "Omstart misslyckades",
};

export function ConfigurationStatusBanner({
  restartRequired,
  configurationActive,
  configurationStatus,
  effectivelyConfigured,
  onApply,
  applyBusy,
  applyError,
}: Props) {
  const needsRestart = restartRequired !== "none" || configurationStatus === "restart_required";
  const statusKey = applyError
    ? "apply_failed"
    : needsRestart
      ? "restart_required"
      : configurationStatus ?? (configurationActive === false ? "restart_required" : effectivelyConfigured ? "active" : "incomplete");
  const label = STATUS_LABELS[statusKey] ?? statusKey;

  if (statusKey === "active" && !applyError) {
    return <p className="config-banner config-banner-success">{label}</p>;
  }

  return (
    <div className="config-banner config-banner-warning" data-testid="configuration-status-banner">
      <p>{label}</p>
      {needsRestart && onApply ? (
        <button type="button" className="config-button-secondary" disabled={applyBusy} onClick={onApply}>
          {applyBusy ? "Tillämpar…" : "Tillämpa ändringar"}
        </button>
      ) : null}
      {applyError ? <p className="config-error-inline">{applyError}</p> : null}
    </div>
  );
}
