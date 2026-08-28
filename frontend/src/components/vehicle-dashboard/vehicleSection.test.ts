import { describe, expect, it, vi } from "vitest";
import { navigateVehicleSection, parseVehicleSection, readVehicleSectionFromLocation } from "./vehicleSection";

describe("vehicleSection parsing", () => {
  it("defaults unknown hash to overview", () => {
    expect(parseVehicleSection("#unknown")).toBe("overview");
  });
});

describe("navigateVehicleSection", () => {
  it("updates url and dispatches hashchange", () => {
    const pushState = vi.spyOn(window.history, "pushState").mockImplementation((_state, _title, url) => {
      if (typeof url === "string") {
        window.history.replaceState(_state, _title, url);
      }
    });
    const listener = vi.fn();
    window.addEventListener("hashchange", listener);

    navigateVehicleSection("akarp", "charging");

    expect(pushState).toHaveBeenCalledWith(null, "", "/sites/akarp/vehicle#laddning");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(readVehicleSectionFromLocation()).toBe("charging");

    pushState.mockRestore();
    window.removeEventListener("hashchange", listener);
  });
});
