import { Icon } from "@/components/dashboard/Icon";

export type StatusTone = "success" | "warning" | "danger" | "neutral";

export function StatusBadge({
  label,
  tone = "neutral",
  showIcon = true,
}: {
  label: string;
  tone?: StatusTone;
  showIcon?: boolean;
}) {
  const iconName = tone === "success" ? "check" : tone === "warning" || tone === "danger" ? "warning" : "check";
  return (
    <span className={`status-badge status-badge-${tone}`} role="status">
      <span className="status-badge-dot" aria-hidden="true" />
      {showIcon && tone !== "neutral" && <Icon name={iconName} />}
      {label}
    </span>
  );
}
