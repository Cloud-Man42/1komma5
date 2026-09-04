import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DisplayEnrollPanel } from "@/components/DisplayEnrollPanel";

const mockFetchSites = vi.fn();
const mockFetchAppleDevices = vi.fn();
const mockCreateAppleDevice = vi.fn();
const mockRevokeAppleDevice = vi.fn();
const mockQrToDataURL = vi.hoisted(() => vi.fn().mockResolvedValue("data:image/png;base64,qr"));

vi.mock("qrcode", () => ({
  default: {
    toDataURL: mockQrToDataURL,
  },
}));

vi.mock("@/lib/api", () => ({
  fetchSites: (...args: unknown[]) => mockFetchSites(...args),
  fetchAppleDevices: (...args: unknown[]) => mockFetchAppleDevices(...args),
  createAppleDevice: (...args: unknown[]) => mockCreateAppleDevice(...args),
  revokeAppleDevice: (...args: unknown[]) => mockRevokeAppleDevice(...args),
}));

describe("DisplayEnrollPanel", () => {
  beforeEach(() => {
    mockFetchSites.mockReset();
    mockFetchAppleDevices.mockReset();
    mockCreateAppleDevice.mockReset();
    mockRevokeAppleDevice.mockReset();

    mockFetchSites.mockResolvedValue([
      { id: 1, slug: "akarp", name: "Åkarp", timezone: "Europe/Stockholm" },
    ]);
    mockFetchAppleDevices.mockResolvedValue([
      {
        id: 9,
        owner_label: "Henrik",
        device_name: "Henriks surfplatta",
        device_type: "tablet",
        token_prefix: "emic_tab",
        scopes: "display.read",
        default_site_slug: "akarp",
        created_at: "2026-08-25T07:00:00Z",
        last_seen_at: null,
        revoked_at: null,
        status: "active",
      },
      {
        id: 1,
        owner_label: "Henrik",
        device_name: "Henriks iPhone widget",
        device_type: "iphone",
        token_prefix: "emic_iph",
        scopes: "widget.read",
        default_site_slug: "akarp",
        created_at: "2026-08-25T07:00:00Z",
        last_seen_at: null,
        revoked_at: null,
        status: "active",
      },
    ]);
  });

  it("lists only display devices", async () => {
    render(<DisplayEnrollPanel />);
    expect(await screen.findByText("Henriks surfplatta")).toBeInTheDocument();
    expect(screen.queryByText("Henriks iPhone widget")).toBeNull();
  });

  it("creates phone device and shows enroll link with qr", async () => {
    mockCreateAppleDevice.mockResolvedValue({
      id: 10,
      owner_label: "Anna",
      device_name: "Annas mobil",
      device_type: "phone",
      token_prefix: "emic_phone",
      scopes: "display.read",
      default_site_slug: "akarp",
      created_at: "2026-08-25T08:00:00Z",
      last_seen_at: null,
      revoked_at: null,
      status: "active",
      token: "emic_phone_token",
    });

    render(<DisplayEnrollPanel />);
    await screen.findByText("Henriks surfplatta");

    fireEvent.change(screen.getByLabelText("Ägare"), { target: { value: "Anna" } });
    fireEvent.change(screen.getByLabelText("Enhetsnamn"), { target: { value: "Annas mobil" } });
    fireEvent.click(screen.getByRole("button", { name: "Skapa aktiveringslänk" }));

    await waitFor(() => {
      expect(mockCreateAppleDevice).toHaveBeenCalledWith({
        owner_label: "Anna",
        device_name: "Annas mobil",
        device_type: "phone",
        default_site_slug: "akarp",
      });
    });

    expect(await screen.findByTestId("display-enroll-result")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Öppna väggdisplay" })).toHaveAttribute(
      "href",
      expect.stringContaining("/api/v1/display/enroll?token=emic_phone_token"),
    );
    await waitFor(() => {
      expect(mockQrToDataURL).toHaveBeenCalled();
      expect(screen.getByAltText("QR-kod för väggdisplay")).toBeInTheDocument();
    });
  });

  it("shows error when device list fails", async () => {
    mockFetchAppleDevices.mockRejectedValue(new Error("offline"));
    render(<DisplayEnrollPanel />);
    expect(await screen.findByText("offline")).toBeInTheDocument();
  });
});
