import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { DisplayOverview } from "@/lib/displayOverview";
import { PiConnectionBanner } from "./PiConnectionBanner";

function freshness(overrides: Partial<DisplayOverview["freshness"]>): DisplayOverview["freshness"] {
  return {
    updated_at: "2026-08-30T10:00:00Z",
    data_age_seconds: 30,
    stale: false,
    connection_state: "CONNECTED",
    ...overrides,
  };
}

describe("PiConnectionBanner", () => {
  it("stays out of the way when the data is live", () => {
    const { container } = render(
      <PiConnectionBanner connection="CONNECTED" freshness={freshness({})} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("warns that readings stopped even though the API answered", () => {
    render(
      <PiConnectionBanner
        connection="CONNECTED"
        freshness={freshness({ stale: true, data_age_seconds: 1_446_120 })}
      />,
    );
    // The regression this guards: a site with no Heartbeat mapping used to
    // present 16-day-old numbers as current, with no banner at all.
    expect(screen.getByRole("status")).toHaveTextContent("Inaktuella värden");
    expect(screen.getByRole("status")).toHaveTextContent("16 dagar sedan senaste mätning");
  });

  it("still names the age when it is only hours old", () => {
    render(
      <PiConnectionBanner
        connection="CONNECTED"
        freshness={freshness({ stale: true, data_age_seconds: 7200 })}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("2 h sedan senaste mätning");
  });

  it("falls back to a bare warning when the age is unknown", () => {
    render(
      <PiConnectionBanner
        connection="CONNECTED"
        freshness={freshness({ stale: true, data_age_seconds: null })}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Inaktuella värden");
    expect(screen.getByRole("status")).not.toHaveTextContent("sedan");
  });

  it("reports lost contact ahead of staleness, since that is the bigger problem", () => {
    render(
      <PiConnectionBanner
        connection="OFFLINE"
        freshness={freshness({ stale: true, data_age_seconds: 99999 })}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Ingen kontakt med EMIC");
  });

  it("shows the reconnecting state while retrying", () => {
    render(<PiConnectionBanner connection="RECONNECTING" />);
    expect(screen.getByRole("status")).toHaveTextContent("Återansluter till EMIC");
  });

  it("says nothing when there is no payload yet on a healthy connection", () => {
    const { container } = render(<PiConnectionBanner connection="CONNECTED" freshness={null} />);
    expect(container).toBeEmptyDOMElement();
  });
});
