export const DISPLAY_DEVICE_TYPES = ["phone", "tablet"] as const;

export type DisplayDeviceType = (typeof DISPLAY_DEVICE_TYPES)[number];

export function isDisplayDevice(device: { scopes?: string | null; device_type?: string | null }): boolean {
  if ((device.scopes ?? "").includes("display.read")) return true;
  const kind = (device.device_type ?? "").toLowerCase();
  return kind === "phone" || kind === "tablet" || kind === "raspberry_pi";
}

export function displayDeviceTypeLabel(deviceType: string): string {
  switch (deviceType.toLowerCase()) {
    case "phone":
      return "Mobil";
    case "tablet":
      return "Surfplatta";
    case "raspberry_pi":
      return "Raspberry Pi";
    default:
      return deviceType;
  }
}

export function buildDisplayEnrollUrl(origin: string, token: string, siteSlug: string): string {
  const base = origin.replace(/\/$/, "");
  const params = new URLSearchParams({ token, slug: siteSlug });
  return `${base}/api/v1/display/enroll?${params.toString()}`;
}

export function displayHomePath(siteSlug: string): string {
  return `/display/${siteSlug}`;
}
