import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChargerSetupWizard } from "@/components/ChargerSetupWizard";

vi.mock("@/lib/api", () => ({
  fetchChargerManufacturers: vi.fn().mockResolvedValue([
    { id: "charge-amps", name: "Charge Amps", model_count: 5 },
    { id: "zaptec", name: "Zaptec", model_count: 4 },
  ]),
  fetchChargerModels: vi.fn().mockResolvedValue([
    {
      id: "halo",
      manufacturer_id: "charge-amps",
      name: "Halo",
      status: "FULL",
      supported_protocols: ["CLOUD_API"],
      integration_methods: ["CHARGE_AMPS_CLOUD"],
      capabilities: { supports_smart_charging: true },
    },
  ]),
  fetchChargerModelDetail: vi.fn().mockResolvedValue({
    model: {
      id: "halo",
      manufacturer_id: "charge-amps",
      name: "Halo",
      status: "FULL",
      supported_protocols: ["CLOUD_API"],
      integration_methods: ["CHARGE_AMPS_CLOUD"],
      capabilities: { supports_smart_charging: true },
    },
    integration_methods: [
      {
        id: "CHARGE_AMPS_CLOUD",
        label: "Charge Amps Cloud API",
        protocol: "CLOUD_API",
        connection_type: "CLOUD",
        recommended: true,
        priority: 1,
        implementation_status: "FULL",
        cloud_dependent: true,
        credential_fields: [{ key: "api_key", label: "API-nyckel", field_type: "password" }],
        connection_fields: [{ key: "charger_id", label: "Laddbox-ID" }],
      },
    ],
  }),
  testEvChargerConnectionDraft: vi.fn().mockResolvedValue({
    success: true,
    status: "CONNECTED",
    message: "Ansluten via Charge Amps Cloud API.",
  }),
  createEvCharger: vi.fn().mockResolvedValue({ id: 1 }),
}));

describe("ChargerSetupWizard", () => {
  it("renders manufacturer and model steps", async () => {
    render(<ChargerSetupWizard siteSlug="akarp" onClose={() => {}} onSaved={() => {}} />);
    expect(await screen.findByText("Lägg till laddbox")).toBeInTheDocument();
    expect(screen.getByText("Charge Amps")).toBeInTheDocument();
  });

  it("loads models after manufacturer selection", async () => {
    const user = userEvent.setup();
    render(<ChargerSetupWizard siteSlug="akarp" onClose={() => {}} onSaved={() => {}} />);
    const manufacturerSelect = await screen.findByRole("combobox", { name: /tillverkare/i });
    await waitFor(() => expect(manufacturerSelect).not.toBeDisabled());
    await user.selectOptions(manufacturerSelect, "charge-amps");
    await waitFor(() => {
      expect(screen.getByText(/Halo \(Full\)/i)).toBeInTheDocument();
    });
  });
});
