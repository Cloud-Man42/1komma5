import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PublishersPanel } from "@/components/modules-devices/PublishersPanel";

vi.mock("next/navigation", () => ({
  usePathname: () => "/config/modules-devices/publishers",
}));

vi.mock("@/lib/adminAuth", () => ({
  getAdminToken: () => "test-token",
}));

const fetchPublisherKeys = vi.fn();
const addPublisherKey = vi.fn();
const revokePublisherKey = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchPublisherKeys: (...args: unknown[]) => fetchPublisherKeys(...args),
  addPublisherKey: (...args: unknown[]) => addPublisherKey(...args),
  revokePublisherKey: (...args: unknown[]) => revokePublisherKey(...args),
}));

describe("PublishersPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchPublisherKeys.mockResolvedValue([
      {
        publisher_id: "emic-internal",
        key_id: "demo-key",
        status: "trusted",
        public_key_hex: "a".repeat(64),
        created_at: null,
        updated_at: null,
      },
    ]);
  });

  it("renders trusted publisher keys", async () => {
    render(<PublishersPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("publishers-panel")).toBeInTheDocument();
      expect(screen.getByText("emic-internal")).toBeInTheDocument();
      expect(screen.getByText("demo-key")).toBeInTheDocument();
    });
  });

  it("submits a new publisher key", async () => {
    addPublisherKey.mockResolvedValue({});
    render(<PublishersPanel />);
    await screen.findByText("emic-internal");
    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0], { target: { value: "new-publisher" } });
    fireEvent.change(inputs[1], { target: { value: "key-1" } });
    fireEvent.change(inputs[2], { target: { value: "b".repeat(64) } });
    fireEvent.click(screen.getByRole("button", { name: "Add key" }));
    await waitFor(() => {
      expect(addPublisherKey).toHaveBeenCalled();
    });
  });
});
