import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppleDevicesAdminPanel } from "@/components/AppleDevicesAdminPanel";

const mockFetchAppleDevices = vi.fn();
const mockCreateAppleDevice = vi.fn();
const mockRevokeAppleDevice = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchAppleDevices: (...args: unknown[]) => mockFetchAppleDevices(...args),
  createAppleDevice: (...args: unknown[]) => mockCreateAppleDevice(...args),
  revokeAppleDevice: (...args: unknown[]) => mockRevokeAppleDevice(...args),
}));

describe("AppleDevicesAdminPanel", () => {
  beforeEach(() => {
    mockFetchAppleDevices.mockReset();
    mockCreateAppleDevice.mockReset();
    mockRevokeAppleDevice.mockReset();
    mockFetchAppleDevices.mockResolvedValue([
      {
        id: 1,
        owner_label: "Henrik",
        device_name: "Henriks iPhone",
        device_type: "iphone",
        token_prefix: "emic_test",
        scopes: "widget.read",
        default_site_slug: "akarp",
        created_at: "2026-08-25T07:00:00Z",
        last_seen_at: null,
        revoked_at: null,
        status: "active",
      },
    ]);
  });

  it("renders device list", async () => {
    render(<AppleDevicesAdminPanel />);
    await waitFor(() => {
      expect(screen.getByText("Henriks iPhone")).toBeInTheDocument();
    });
    expect(screen.getByText("Henrik")).toBeInTheDocument();
  });

  it("shows one-time token after create", async () => {
    mockCreateAppleDevice.mockResolvedValue({
      id: 2,
      owner_label: "Anna",
      device_name: "Annas iPhone",
      device_type: "iphone",
      token_prefix: "emic_newtok",
      scopes: "widget.read",
      default_site_slug: "akarp",
      created_at: "2026-08-25T07:10:00Z",
      last_seen_at: null,
      revoked_at: null,
      status: "active",
      token: "emic_secret_token_value",
    });
    render(<AppleDevicesAdminPanel />);
    await waitFor(() => screen.getByText("Henriks iPhone"));

    fireEvent.change(screen.getByLabelText("Ägare"), { target: { value: "Anna" } });
    fireEvent.change(screen.getByLabelText("Enhetsnamn"), { target: { value: "Annas iPhone" } });
    fireEvent.click(screen.getByRole("button", { name: "Skapa enhet" }));

    await waitFor(() => {
      expect(screen.getByTestId("apple-device-token-once")).toBeInTheDocument();
    });
    expect(screen.getByText("emic_secret_token_value")).toBeInTheDocument();
  });

  it("shows error when list fails", async () => {
    mockFetchAppleDevices.mockRejectedValue(new Error("Serverfel"));
    render(<AppleDevicesAdminPanel />);
    await waitFor(() => {
      expect(screen.getByText("Serverfel")).toBeInTheDocument();
    });
  });
});
