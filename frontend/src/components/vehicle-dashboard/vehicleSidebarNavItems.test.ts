import { describe, expect, it } from "vitest";
import {
  isVehicleSectionActive,
  parseVehicleSection,
  vehicleSectionHref,
} from "./vehicleSection";
import { isVehicleSidebarNavActive, VEHICLE_SIDEBAR_NAV } from "./vehicleSidebarNavItems";

describe("vehicleSection", () => {
  it("parses hash to section id", () => {
    expect(parseVehicleSection("")).toBe("overview");
    expect(parseVehicleSection("#laddning")).toBe("charging");
    expect(parseVehicleSection("#resor")).toBe("history");
    expect(parseVehicleSection("#status")).toBe("status");
    expect(parseVehicleSection("#kostnad")).toBe("costs");
    expect(parseVehicleSection("#schema")).toBe("schedule");
    expect(parseVehicleSection("#installningar")).toBe("settings");
  });

  it("builds section hrefs", () => {
    expect(vehicleSectionHref("akarp", "overview")).toBe("/sites/akarp/vehicle");
    expect(vehicleSectionHref("akarp", "charging")).toBe("/sites/akarp/vehicle#laddning");
  });

  it("detects active section from hash", () => {
    expect(isVehicleSectionActive("/sites/akarp/vehicle", "akarp", "charging", "#laddning")).toBe(true);
    expect(isVehicleSectionActive("/sites/akarp/vehicle", "akarp", "overview", "")).toBe(true);
    expect(isVehicleSectionActive("/sites/akarp/vehicle", "akarp", "overview", "#laddning")).toBe(false);
  });
});

describe("vehicleSidebarNavItems", () => {
  it("marks matching sidebar item active", () => {
    const charging = VEHICLE_SIDEBAR_NAV.find((item) => item.id === "charging");
    expect(isVehicleSidebarNavActive("/sites/akarp/vehicle", "akarp", charging!, "#laddning")).toBe(true);
  });

  it("marks overview active without hash", () => {
    const overview = VEHICLE_SIDEBAR_NAV.find((item) => item.id === "overview");
    expect(isVehicleSidebarNavActive("/sites/akarp/vehicle", "akarp", overview!, "")).toBe(true);
  });

  it("settings stays on vehicle page", () => {
    const settings = VEHICLE_SIDEBAR_NAV.find((item) => item.id === "settings");
    expect(settings?.href("akarp")).toBe("/sites/akarp/vehicle#installningar");
  });
});
