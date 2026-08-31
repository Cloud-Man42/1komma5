import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PiTouchCard } from "./PiTouchCard";

describe("PiTouchCard", () => {
  it("renders an accessible link without opening a new tab", () => {
    render(
      <PiTouchCard href="/display/akarp/solar" className="pi-card" ariaLabel="Öppna Sol-vyn">
        <span>Sol</span>
      </PiTouchCard>,
    );

    const link = screen.getByRole("link", { name: "Öppna Sol-vyn" });
    expect(link).toHaveAttribute("href", "/display/akarp/solar");
    expect(link).not.toHaveAttribute("target");
    expect(link.querySelector(".pi-touch-chevron")).toHaveAttribute("aria-hidden", "true");
  });
});
