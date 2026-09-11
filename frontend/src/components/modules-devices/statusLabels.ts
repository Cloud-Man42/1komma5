export function runtimeStatusLabel(status: string): string {
  switch (status) {
    case "running":
      return "Aktiv";
    case "starting":
      return "Startar";
    case "stopping":
      return "Stoppar";
    case "stopped":
      return "Stoppad";
    case "failed":
      return "Fel";
    case "blocked":
      return "Blockerad";
    case "unknown":
      return "Runtime status unavailable";
    default:
      return status;
  }
}

export function healthStatusLabel(status: string): string {
  switch (status) {
    case "healthy":
      return "Frisk";
    case "degraded":
      return "Degraderad";
    case "unhealthy":
      return "Ohälsosam";
    case "unknown":
      return "Okänd";
    default:
      return status;
  }
}

export function healthTone(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "healthy") return "success";
  if (status === "degraded") return "warning";
  if (status === "unhealthy") return "danger";
  return "neutral";
}

export function runtimeTone(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "running") return "success";
  if (status === "starting" || status === "stopping") return "warning";
  if (status === "failed" || status === "blocked") return "danger";
  return "neutral";
}
