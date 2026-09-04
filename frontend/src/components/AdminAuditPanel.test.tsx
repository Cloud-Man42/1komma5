import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AdminAuditPanel } from "./AdminAuditPanel";
import type { AdminAuditLog } from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchAdminAuditLog: vi.fn(),
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: vi.fn(),
}));

import { fetchAdminAuditLog } from "@/lib/api";
import { getAdminToken } from "@/lib/adminAuth";

const sample: AdminAuditLog = {
  entries: [
    {
      id: 1,
      recorded_at: "2026-09-04T04:00:00Z",
      http_method: "PUT",
      path: "/api/sites/akarp/spa/config",
      action: "spa.config.update",
      site_slug: "akarp",
      resource_type: "spa",
      resource_id: "3",
      outcome: "success",
      summary: { integration_enabled: true },
    },
  ],
};

describe("AdminAuditPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("prompts for admin token when missing", () => {
    vi.mocked(getAdminToken).mockReturnValue("");
    render(<AdminAuditPanel />);
    expect(screen.getByText(/Ange admin-token ovan/i)).toBeInTheDocument();
  });

  it("renders audit entries when token is set", async () => {
    vi.mocked(getAdminToken).mockReturnValue("secret");
    vi.mocked(fetchAdminAuditLog).mockResolvedValue(sample);
    render(<AdminAuditPanel />);
    expect(await screen.findByText("spa.config.update")).toBeInTheDocument();
    expect(screen.getByText("akarp")).toBeInTheDocument();
  });

  it("shows error on fetch failure", async () => {
    vi.mocked(getAdminToken).mockReturnValue("secret");
    vi.mocked(fetchAdminAuditLog).mockRejectedValue(new Error("401"));
    render(<AdminAuditPanel />);
    expect(await screen.findByText("401")).toBeInTheDocument();
  });
});
