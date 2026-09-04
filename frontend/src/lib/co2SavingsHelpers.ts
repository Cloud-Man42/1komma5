/** Swedish grid average emission factor (kg CO2 per kWh self-consumed solar). */
export const GRID_EMISSION_KG_PER_KWH = 0.045;

export function estimateCo2AvoidedKg(solarKwh: number | null | undefined): number | null {
  if (solarKwh == null || solarKwh <= 0) {
    return null;
  }
  return solarKwh * GRID_EMISSION_KG_PER_KWH;
}

export function formatCo2AvoidedKg(kg: number | null): string {
  if (kg == null) {
    return "—";
  }
  if (kg < 1) {
    return `${Math.round(kg * 1000)} g`;
  }
  return `${kg.toFixed(1)} kg`;
}
