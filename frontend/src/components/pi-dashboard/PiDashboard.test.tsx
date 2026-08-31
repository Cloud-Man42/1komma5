import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MOCKUP_NOW, MOCKUP_OVERVIEW } from "./__fixtures__/mockupOverview";
import { PiDashboard } from "./PiDashboard";
import { PI_CARD_SECTIONS, PI_SECTION_META, piHref } from "./piSections";

function renderDashboard(props: Partial<Parameters<typeof PiDashboard>[0]> = {}) {
  return render(
    <PiDashboard
      slug="preview"
      data={MOCKUP_OVERVIEW}
      connection="CONNECTED"
      error={null}
      nowOverride={MOCKUP_NOW}
      {...props}
    />,
  );
}

describe("PiDashboard structure", () => {
  it("renders every panel the reference layout requires, in order", () => {
    renderDashboard();
    const titles = screen
      .getAllByRole("heading", { level: 2 })
      .map((node) => node.textContent);
    expect(titles).toEqual([
      "SOLPRODUKTION",
      "HUSFÖRBRUKNING",
      "BATTERI",
      "NETTO MOT NÄT",
      "SOLÖVERSKOTT",
      "ENERGIFLÖDE – JUST NU",
      "FORDON – MERCEDES EQE 500",
      "LADDBOX – CHARGEAMPS HALO",
      "SPA – ARCTIC SPA",
      "EKONOMI – DENNA MÅNAD",
      "DAGENS HÖJDPUNKTER",
    ]);
  });

  it("appends the vehicle model to the heading only when it adds information", () => {
    const cases: [{ display_name: string | null; model: string | null }, string][] = [
      [{ display_name: "Mercedes", model: "EQE 500" }, "FORDON – MERCEDES EQE 500"],
      [{ display_name: "Mercedes-Benz", model: "Mercedes-Benz" }, "FORDON – MERCEDES-BENZ"],
      [{ display_name: "Mercedes EQE 500", model: "EQE 500" }, "FORDON – MERCEDES EQE 500"],
      [{ display_name: null, model: "EQE 500" }, "FORDON – EQE 500"],
      [{ display_name: null, model: null }, "FORDON"],
    ];

    for (const [vehicle, expected] of cases) {
      const { unmount } = renderDashboard({
        data: { ...MOCKUP_OVERVIEW, vehicle: { ...MOCKUP_OVERVIEW.vehicle, ...vehicle } },
      });
      expect(screen.getByRole("heading", { level: 2, name: expected })).toBeTruthy();
      unmount();
    }
  });

  it("does not render the old sidebar navigation", () => {
    renderDashboard();
    expect(screen.queryByRole("navigation", { name: "Sektioner" })).not.toBeInTheDocument();
    expect(screen.queryByText("Inställningar")).not.toBeInTheDocument();
  });

  it("shows the Home button and EMIC brand in the header", () => {
    renderDashboard();
    expect(screen.getByRole("link", { name: "Hem" })).toHaveAttribute("href", "/display/preview");
    expect(screen.getByText("EMIC")).toBeInTheDocument();
    expect(screen.getByText("ENERGY INTELLIGENCE")).toBeInTheDocument();
  });

  it("renders the bottom KPI row", () => {
    renderDashboard();
    for (const label of [
      "TOTAL PRODUKTION",
      "TOTAL FÖRBRUKNING",
      "BATTERI SOH",
      "SJÄLVFÖRSÖRJNING",
      "EGENANVÄNDNING",
      "AKTIV PRISNIVÅ",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });
});

describe("PiDashboard touch navigation", () => {
  const expectedHrefs = [
    piHref("preview", PI_CARD_SECTIONS.solarProduction),
    piHref("preview", PI_CARD_SECTIONS.houseConsumption),
    piHref("preview", PI_CARD_SECTIONS.battery),
    piHref("preview", PI_CARD_SECTIONS.gridNet),
    piHref("preview", PI_CARD_SECTIONS.solarSurplus),
    piHref("preview", PI_CARD_SECTIONS.energyFlow),
    piHref("preview", PI_CARD_SECTIONS.vehicle),
    piHref("preview", PI_CARD_SECTIONS.charger),
    piHref("preview", PI_CARD_SECTIONS.spa),
    piHref("preview", PI_CARD_SECTIONS.economy),
    piHref("preview", PI_CARD_SECTIONS.highlights),
    piHref("preview", PI_CARD_SECTIONS.kpiProduction),
    piHref("preview", PI_CARD_SECTIONS.kpiConsumption),
    piHref("preview", PI_CARD_SECTIONS.kpiBatterySoh),
    piHref("preview", PI_CARD_SECTIONS.kpiSelfSufficiency),
    piHref("preview", PI_CARD_SECTIONS.kpiSelfUse),
    piHref("preview", PI_CARD_SECTIONS.kpiPrice),
  ];

  it("wraps every major card and KPI cell in a same-tab link", () => {
    renderDashboard();
    const links = screen.getAllByRole("link");
    for (const href of expectedHrefs) {
      const match = links.find((link) => link.getAttribute("href") === href);
      expect(match, `missing link for ${href}`).toBeTruthy();
      expect(match).not.toHaveAttribute("target");
    }
  });

  it("uses touch labels on the primary cards", () => {
    renderDashboard();
    expect(screen.getAllByRole("link", { name: PI_SECTION_META.solar.touchLabel }).length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByRole("link", { name: PI_SECTION_META.grid.touchLabel }).length).toBeGreaterThanOrEqual(2);
  });

  it("maps KPI bar cells to their detail routes", () => {
    renderDashboard({ slug: "akarp" });
    expect(screen.getByRole("link", { name: /TOTAL PRODUKTION/i })).toHaveAttribute(
      "href",
      piHref("akarp", PI_CARD_SECTIONS.kpiProduction),
    );
    expect(screen.getByRole("link", { name: /AKTIV PRISNIVÅ/i })).toHaveAttribute(
      "href",
      piHref("akarp", PI_CARD_SECTIONS.kpiPrice),
    );
  });
});

describe("PiDashboard values", () => {
  it("shows the live readings with the reference number format", () => {
    renderDashboard();
    expect(screen.getAllByText("3.25")).toHaveLength(2);
    expect(screen.getByText("Idag: 24.7 kWh")).toBeInTheDocument();
    expect(screen.getByText("58")).toBeInTheDocument();
    expect(screen.getByText("7.8 kWh / 13.5 kWh")).toBeInTheDocument();
    expect(screen.getByText(/^2.846 kr$/)).toBeInTheDocument();
    expect(screen.getByText("+912 kr")).toBeInTheDocument();
    expect(screen.getByText("200.6 öre/kWh")).toBeInTheDocument();
  });

  it("shows the header clock and site status", () => {
    renderDashboard();
    expect(screen.getByText("Åkarp")).toBeInTheDocument();
    expect(screen.getByText("ONLINE")).toBeInTheDocument();
    expect(screen.getByText("08:08")).toBeInTheDocument();
    expect(screen.getByText("Sist uppdaterad: 08:08:07")).toBeInTheDocument();
  });
});

describe("PiDashboard degraded states", () => {
  it("keeps the full panel structure and shows placeholders when there is no data", () => {
    renderDashboard({ data: null });
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(11);
    expect(screen.getAllByText("--").length).toBeGreaterThan(5);
    expect(screen.queryByText("0 kW")).not.toBeInTheDocument();
  });

  it("labels unavailable sections rather than showing a fake zero", () => {
    renderDashboard({
      data: {
        ...MOCKUP_OVERVIEW,
        spa: { ...MOCKUP_OVERVIEW.spa, available: false },
        vehicle: { ...MOCKUP_OVERVIEW.vehicle, available: false },
      },
    });
    expect(screen.getAllByText("Data saknas").length).toBeGreaterThan(0);
  });

  it("shows a reconnect banner while reconnecting", () => {
    renderDashboard({ connection: "RECONNECTING" });
    expect(screen.getByRole("status")).toHaveTextContent("Återansluter till EMIC");
  });

  it("shows an offline banner when EMIC cannot be reached", () => {
    renderDashboard({ connection: "OFFLINE", data: null, error: "fetch failed" });
    expect(screen.getByRole("status")).toHaveTextContent("Ingen kontakt med EMIC");
    expect(screen.getByText("OFFLINE")).toBeInTheDocument();
  });

  it("renders no banner while connected", () => {
    renderDashboard();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
