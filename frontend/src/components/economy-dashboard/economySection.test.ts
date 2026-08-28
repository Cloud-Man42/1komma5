import { describe, expect, it, vi } from "vitest";
import {
  navigateEconomySection,
  parseEconomySection,
  readEconomySectionFromLocation,
} from "./economySection";

describe("economySection parsing", () => {
  it("defaults unknown hash to analysis", () => {
    expect(parseEconomySection("#unknown")).toBe("analysis");
  });

  it("parses detail section hashes", () => {
    expect(parseEconomySection("#kassaflode")).toBe("cashflow");
    expect(parseEconomySection("#insikter")).toBe("insights");
    expect(parseEconomySection("#priser")).toBe("prices");
  });
});

describe("navigateEconomySection", () => {
  it("updates url and dispatches hashchange", () => {
    const pushState = vi.spyOn(window.history, "pushState").mockImplementation((_state, _title, url) => {
      if (typeof url === "string") {
        window.history.replaceState(_state, _title, url);
      }
    });
    const listener = vi.fn();
    window.addEventListener("hashchange", listener);

    navigateEconomySection("akarp", "reports");

    expect(pushState).toHaveBeenCalledWith(null, "", "/sites/akarp/costs#rapporter");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(readEconomySectionFromLocation()).toBe("reports");

    pushState.mockRestore();
    window.removeEventListener("hashchange", listener);
  });
});
