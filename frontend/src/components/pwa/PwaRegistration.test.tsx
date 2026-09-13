import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PwaRegistration } from "./PwaRegistration";

describe("PwaRegistration", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "navigator",
      {
        serviceWorker: {
          getRegistrations: vi.fn().mockResolvedValue([{ unregister: vi.fn().mockResolvedValue(true) }]),
          register: vi.fn().mockResolvedValue({ update: vi.fn().mockResolvedValue(undefined) }),
        },
      },
    );
  });

  it("unregisters old service workers once before registering v4", async () => {
    render(<PwaRegistration />);
    await waitFor(() => {
      expect(navigator.serviceWorker.getRegistrations).toHaveBeenCalled();
      expect(navigator.serviceWorker.register).toHaveBeenCalledWith("/sw.js", {
        scope: "/",
        updateViaCache: "none",
      });
      expect(localStorage.getItem("emic-sw-v4-migrated")).toBe("1");
    });
  });
});
