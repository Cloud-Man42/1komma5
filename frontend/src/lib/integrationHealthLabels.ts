export const INTEGRATION_PROVIDER_LABELS_SV: Record<string, string> = {
  heartbeat: "Heartbeat",
  price_engine: "Prismotor",
  solar_forecast: "Solprognos",
  arctic_spa: "Arctic Spa",
  energy_control: "Energistyrning",
  mercedes: "Mercedes me",
  chargefinder: "ChargeFinder",
};

export function integrationProviderLabelSv(provider: string): string {
  return INTEGRATION_PROVIDER_LABELS_SV[provider] ?? provider;
}
