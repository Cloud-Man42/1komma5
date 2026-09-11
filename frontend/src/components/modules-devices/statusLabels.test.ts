import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { healthStatusLabel, runtimeStatusLabel } from "./statusLabels";

describe("statusLabels", () => {
  it("maps unknown runtime to unavailable label", () => {
    expect(runtimeStatusLabel("unknown")).toBe("Runtime status unavailable");
  });

  it("maps healthy health status", () => {
    expect(healthStatusLabel("healthy")).toBe("Frisk");
  });
});
