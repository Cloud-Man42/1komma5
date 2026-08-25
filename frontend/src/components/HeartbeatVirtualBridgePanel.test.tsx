import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HeartbeatVirtualBridgePanel } from "@/components/HeartbeatVirtualBridgePanel";

const mockFetchStatus = vi.fn();
const mockFetchSettings = vi.fn();
const mockRunDiscovery = vi.fn();
const mockFetchRun = vi.fn();
const mockFetchDecisions = vi.fn();

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchHeartbeatBridgeStatus: (...args: unknown[]) => mockFetchStatus(...args),
    fetchHeartbeatBridgeSettings: (...args: unknown[]) => mockFetchSettings(...args),
    fetchHeartbeatBridgeDecisions: (...args: unknown[]) => mockFetchDecisions(...args),
    runHeartbeatDiscovery: (...args: unknown[]) => mockRunDiscovery(...args),
    fetchHeartbeatDiscoveryRun: (...args: unknown[]) => mockFetchRun(...args),
    runHeartbeatWriteTest: vi.fn(),
    runHeartbeatReplay: vi.fn(),
    updateHeartbeatBridgeSettings: vi.fn(),
  };
});

describe("HeartbeatVirtualBridgePanel", () => {
  beforeEach(() => {
    mockFetchDecisions.mockResolvedValue([]);
    mockFetchStatus.mockResolvedValue({
      heartbeat_connection: "ONLINE",
      ev_profile: "NOT FOUND",
      ev_id: null,
      confidence_pct: null,
      physical_hb_wallbox: "UNKNOWN",
      charge_amps_halo: "FOUND",
      halo_online: true,
      virtual_bridge: "NOT READY",
      setup_classification: null,
      bridge_lifecycle: "DISABLED",
      simulation_mode: true,
      physical_control: "DISABLED",
      write_enabled: false,
      settings: {},
      mappings: [],
    });
    mockFetchSettings.mockResolvedValue({
      site_id: 1,
      discovery_enabled: true,
      write_enabled: false,
      virtual_bridge_enabled: false,
      physical_control_enabled: false,
      soc_sync_enabled: false,
      replay_enabled: true,
      simulation_mode: true,
      confidence_threshold_pct: 90,
      battery_priority_mode: "BATTERY_FIRST",
    });
  });

  it("renders bridge status and discovery button", async () => {
    render(<HeartbeatVirtualBridgePanel siteSlug="akarp" />);
    expect(await screen.findByText(/Heartbeat Virtual EV Bridge/i)).toBeTruthy();
    expect(screen.getByRole("button", { name: /RUN HEARTBEAT EV DISCOVERY/i })).toBeTruthy();
  });

  it("runs discovery and shows report", async () => {
    mockRunDiscovery.mockResolvedValue({
      run_id: 7,
      report_text: "EMIC HEARTBEAT EV DISCOVERY RESULT",
      setup_classification: "C",
      bridge_lifecycle: "VIRTUAL_CHARGER_BRIDGE_CANDIDATE",
      resolved_ev_id: "ev-1",
      confidence_pct: 95,
      virtual_bridge_suitable: true,
      charging_modes: ["SMART_CHARGE"],
      emic_vehicle_lines: [],
      warnings: [],
    });
    mockFetchRun.mockResolvedValue({
      id: 7,
      observations: [{ method: "GET", path: "/v1/systems/x/devices/evs", status_code: 200, duration_ms: 42, raw_json: {} }],
    });

    render(<HeartbeatVirtualBridgePanel siteSlug="akarp" />);
    await userEvent.click(await screen.findByRole("button", { name: /RUN HEARTBEAT EV DISCOVERY/i }));

    await waitFor(() => {
      expect(screen.getByText(/EMIC HEARTBEAT EV DISCOVERY RESULT/)).toBeTruthy();
    });
  });

  it("shows simulation decision timeline", async () => {
    mockFetchDecisions.mockResolvedValue([
      {
        bridge_state: "SIMULATION",
        heartbeat_ev_id: null,
        heartbeat_mode: "SMART_CHARGE",
        ai_decision: null,
        reason: "EMS activeChargingMode",
        recorded_at: "2026-08-24T12:00:00Z",
      },
    ]);
    render(<HeartbeatVirtualBridgePanel siteSlug="akarp" />);
    expect(await screen.findByText(/Virtual charger decisions/i)).toBeTruthy();
    expect(screen.getByText(/EMS activeChargingMode/)).toBeTruthy();
  });

  it("shows error when status fetch fails", async () => {
    mockFetchStatus.mockRejectedValue(new Error("Network error"));
    render(<HeartbeatVirtualBridgePanel siteSlug="akarp" />);
    expect(await screen.findByText(/Network error/i)).toBeTruthy();
  });
});
