import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PiHomeButton } from "./PiHomeButton";

describe("PiHomeButton", () => {
  it("links to the Pi home route with aria-label Hem", () => {
    render(<PiHomeButton slug="akarp" />);
    const home = screen.getByRole("link", { name: "Hem" });
    expect(home).toHaveAttribute("href", "/display/akarp");
    expect(home).not.toHaveAttribute("aria-current");
  });

  it("marks the home view as the current page", () => {
    render(<PiHomeButton slug="preview" isHome />);
    expect(screen.getByRole("link", { name: "Hem" })).toHaveAttribute("aria-current", "page");
  });
});
