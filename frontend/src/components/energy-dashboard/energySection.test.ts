import { describe, expect, it, vi } from "vitest";
import {
  navigateEnergySection,
  parseEnergySection,
  readEnergySectionFromLocation,
} from "./energySection";

describe("energySection parsing", () => {
  it("defaults unknown hash to flow", () => {
    expect(parseEnergySection("#unknown")).toBe("flow");
  });

  it("parses section hashes", () => {
    expect(parseEnergySection("#historik")).toBe("history");
    expect(parseEnergySection("#floden")).toBe("flows");
  });
});

describe("navigateEnergySection", () => {
  it("updates url and dispatches hashchange", () => {
    const pushState = vi.spyOn(window.history, "pushState").mockImplementation((_state, _title, url) => {
      if (typeof url === "string") {
        window.history.replaceState(_state, _title, url);
      }
    });
    const listener = vi.fn();
    window.addEventListener("hashchange", listener);

    navigateEnergySection("akarp", "history");

    expect(pushState).toHaveBeenCalledWith(null, "", "/sites/akarp/energy#historik");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(readEnergySectionFromLocation()).toBe("history");

    pushState.mockRestore();
    window.removeEventListener("hashchange", listener);
  });
});
