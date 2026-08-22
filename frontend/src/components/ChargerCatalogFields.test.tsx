import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChargerCatalogFields, isSmartChargingAvailable } from "@/components/ChargerCatalogFields";

vi.mock("@/lib/api", () => ({
  fetchChargerManufacturers: vi.fn().mockResolvedValue([
    { id: "charge-amps", name: "Charge Amps", model_count: 5 },
    { id: "zaptec", name: "Zaptec", model_count: 4 },
  ]),
  fetchChargerModels: vi.fn().mockImplementation((manufacturerId: string) => {
    if (manufacturerId === "zaptec") {
      return Promise.resolve([
        {
          id: "go",
          manufacturer_id: "zaptec",
          name: "Go",
          status: "UNSUPPORTED",
          supported_protocols: [],
          integration_methods: ["ZAPTEC_REST"],
          capabilities: {},
        },
      ]);
    }
    return Promise.resolve([
      {
        id: "halo",
        manufacturer_id: "charge-amps",
        name: "Halo",
        status: "FULL",
        supported_protocols: ["CLOUD_API"],
        integration_methods: ["CHARGE_AMPS_CLOUD"],
        capabilities: {},
      },
    ]);
  }),
  fetchChargerModelDetail: vi.fn().mockResolvedValue({
    model: { id: "halo", name: "Halo", status: "FULL" },
    integration_methods: [
      {
        id: "CHARGE_AMPS_CLOUD",
        label: "Charge Amps Cloud API",
        connection_type: "CLOUD",
        recommended: true,
        implementation_status: "FULL",
      },
    ],
  }),
}));

describe("ChargerCatalogFields", () => {
  it("renders manufacturer and model dropdowns", async () => {
    render(
      <ChargerCatalogFields
        value={{ manufacturerId: "", modelId: "", integrationMethod: "" }}
        onChange={() => {}}
      />,
    );
    expect(await screen.findByLabelText(/tillverkare/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/modell/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/integrationsmetod/i)).toBeInTheDocument();
  });

  it("loads models when manufacturer selected", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ChargerCatalogFields
        value={{ manufacturerId: "", modelId: "", integrationMethod: "" }}
        onChange={onChange}
      />,
    );
    await user.selectOptions(await screen.findByLabelText(/tillverkare/i), "charge-amps");
    expect(onChange).toHaveBeenCalledWith({
      manufacturerId: "charge-amps",
      modelId: "",
      integrationMethod: "",
    });
  });

  it("shows smart charging available for implemented integration", async () => {
    const user = userEvent.setup();
    render(
      <ChargerCatalogFields
        value={{ manufacturerId: "charge-amps", modelId: "halo", integrationMethod: "CHARGE_AMPS_CLOUD" }}
        onChange={() => {}}
      />,
    );
    await user.selectOptions(await screen.findByLabelText(/tillverkare/i), "charge-amps");
    expect(await screen.findByText(/Smartladdning och styrning är tillgängliga/i)).toBeInTheDocument();
  });

  it("warns when integration method is unsupported", async () => {
    const { fetchChargerModelDetail } = await import("@/lib/api");
    vi.mocked(fetchChargerModelDetail).mockResolvedValueOnce({
      model: {
        id: "go",
        manufacturer_id: "zaptec",
        name: "Go",
        status: "UNSUPPORTED",
        supported_protocols: [],
        integration_methods: ["ZAPTEC_REST"],
        capabilities: {},
      },
      integration_methods: [
        {
          id: "ZAPTEC_REST",
          label: "Zaptec REST API",
          protocol: "REST",
          connection_type: "CLOUD",
          recommended: true,
          priority: 1,
          implementation_status: "UNSUPPORTED",
          cloud_dependent: true,
          credential_fields: [],
          connection_fields: [],
        },
      ],
    });

    render(
      <ChargerCatalogFields
        value={{ manufacturerId: "zaptec", modelId: "go", integrationMethod: "ZAPTEC_REST" }}
        onChange={() => {}}
      />,
    );

    expect(
      await screen.findByText(/Integrationen Zaptec REST API är ännu inte implementerad/i),
    ).toBeInTheDocument();
    expect(isSmartChargingAvailable({ implementation_status: "UNSUPPORTED" } as never)).toBe(false);
  });
});
