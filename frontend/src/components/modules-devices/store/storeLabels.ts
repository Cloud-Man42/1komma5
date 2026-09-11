/** Store UI label helpers — display backend enums only. */

export function primaryActionLabel(action: string): string {
  const map: Record<string, string> = {
    INSTALL: "Install",
    UPDATE: "Update",
    INSTALLED: "Installed",
    STAGED: "Staged",
    SECURITY_REVIEW_REQUIRED: "Security review required",
    BLOCKED_BY_POLICY: "Blocked by policy",
    RUNTIME_NOT_PERMITTED: "Runtime not yet permitted",
    REVOKED: "Revoked",
    INCOMPATIBLE: "Incompatible",
    NONE: "—",
  };
  return map[action] ?? action;
}

export function trustBadgeClass(tier: string): string {
  if (tier === "OFFICIAL") return "config-badge success";
  if (tier === "VERIFIED" || tier === "ORG_APPROVED") return "config-badge";
  if (tier === "COMMUNITY") return "config-badge warn";
  if (tier === "REVOKED") return "config-badge danger";
  return "config-badge";
}

export function originLabel(origin: string): string {
  const map: Record<string, string> = {
    BUILT_IN: "Built-in",
    INTERNAL_STORE: "Internal Store",
    ORGANIZATION: "Organization",
    PUBLIC_MARKETPLACE: "Public Marketplace",
    INSTALLED: "Installed",
  };
  return map[origin] ?? origin;
}

export function securityBadgeClass(badge: string): string {
  if (badge === "CRITICAL_ADVISORY" || badge === "REVOKED") return "config-badge danger";
  if (badge === "SECURITY_REVIEW_REQUIRED") return "config-badge warn";
  if (badge === "NO_CRITICAL_ISSUES" || badge === "VERIFIED_ARTIFACT") return "config-badge success";
  return "config-badge";
}

export function isActionable(action: string): boolean {
  return action === "INSTALL" || action === "UPDATE";
}
