import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DiscoverView } from "@/components/modules-devices/store/DiscoverView";
import { ModuleCard } from "@/components/modules-devices/store/ModuleCard";
import type { StoreModuleSummary } from "@/lib/api";

const { cardModule } = vi.hoisted(() => ({
  cardModule: {
    module_id: "integration.demo",
    display_name: "Demo Module",
    publisher_id: "emic",
    publisher_name: "EMIC",
    description: "Test module",
    category: "Monitoring",
    categories: ["Monitoring"],
    icon_url: null,
    origin: "BUILT_IN",
    trust_tier: "OFFICIAL",
    trust_badge: "OFFICIAL",
    security_badge: "NO_CRITICAL_ISSUES",
    installed_state: "INSTALLED",
    installed_version: "1.0.0",
    latest_version: "1.0.0",
    update_available: false,
    compatible: true,
    control_capable: false,
    primary_action: "INSTALLED",
    policy: { decision: "ALLOW", reason_codes: [], explanation: "Allowed" },
  } satisfies StoreModuleSummary,
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "test-token",
}));

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    fetchStoreCatalog: vi.fn().mockResolvedValue({
      modules: [cardModule],
      page: 1,
      page_size: 48,
      total: 1,
      categories: [{ id: "Monitoring", label: "Monitoring", count: 1 }],
      marketplace_status: { message: "OK" },
    }),
    fetchStoreStatus: vi.fn().mockResolvedValue({
      marketplace_enabled: true,
      metadata_health: "healthy",
      message: "Marketplace healthy",
      offline: false,
      stale: false,
      invalid: false,
      last_success: "2026-09-08T12:00:00Z",
    }),
  };
});

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/store",
}));

describe("ModuleCard", () => {
  it("renders module summary from backend", () => {
    render(<ModuleCard module={cardModule} />);
    expect(screen.getByText("Demo Module")).toBeInTheDocument();
    expect(screen.getByText("OFFICIAL")).toBeInTheDocument();
  });

  it("shows control notice when control_capable", () => {
    render(<ModuleCard module={{ ...cardModule, control_capable: true }} />);
    expect(screen.getByTestId("control-notice")).toBeInTheDocument();
  });
});

describe("DiscoverView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads catalog and shows status banner", async () => {
    render(<DiscoverView />);
    await waitFor(() => {
      expect(screen.getByTestId("store-status-banner")).toHaveTextContent("Marketplace healthy");
    });
    await waitFor(() => {
      expect(screen.getAllByTestId("store-card-integration.demo").length).toBeGreaterThan(0);
    });
  });
});
