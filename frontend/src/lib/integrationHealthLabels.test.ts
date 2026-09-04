import { describe, expect, it } from "vitest";

import { integrationProviderLabelSv } from "@/lib/integrationHealthLabels";

describe("integrationHealthLabels", () => {
  it("maps known providers to Swedish labels", () => {
    expect(integrationProviderLabelSv("heartbeat")).toBe("Heartbeat");
    expect(integrationProviderLabelSv("price_engine")).toBe("Prismotor");
  });

  it("falls back to raw provider id", () => {
    expect(integrationProviderLabelSv("custom_provider")).toBe("custom_provider");
  });
});
