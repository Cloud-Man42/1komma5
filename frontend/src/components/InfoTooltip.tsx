interface InfoTooltipProps {
  label: string;
  text: string;
  className?: string;
}

export function InfoTooltip({ label, text, className }: InfoTooltipProps) {
  const dtClassName = className ? `${className} finance-card-label` : "finance-card-label";

  return (
    <dt className={dtClassName} title={text} aria-label={`${label}. ${text}`}>
      {label}{" "}
      <span className="muted finance-info-icon" aria-hidden="true">
        ⓘ
      </span>
    </dt>
  );
}
