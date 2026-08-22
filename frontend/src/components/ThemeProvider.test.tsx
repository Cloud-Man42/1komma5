import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ThemeToggle } from "@/components/ThemeToggle";

describe("ThemeProvider", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("sets data-theme on html and toggles", () => {
    render(
      <ThemeProvider>
        <ThemeToggle />
      </ThemeProvider>,
    );

    const button = screen.getByRole("button", { name: /läge/i });
    const initial = document.documentElement.getAttribute("data-theme");
    fireEvent.click(button);
    const next = document.documentElement.getAttribute("data-theme");
    expect(next).not.toBe(initial);
    expect(window.localStorage.getItem("emic-theme")).toBe(next);
  });
});
