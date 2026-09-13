import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MobileEnergyHubPage from "./page";

describe("MobileEnergyHubPage", () => {
  it("renders native energy section cards", () => {
    render(<MobileEnergyHubPage />);
    expect(screen.getByText("Solar")).toBeInTheDocument();
    expect(screen.getByText("Battery")).toBeInTheDocument();
    expect(screen.getByText("Grid")).toBeInTheDocument();
    expect(screen.getByText("History")).toBeInTheDocument();
  });
});
