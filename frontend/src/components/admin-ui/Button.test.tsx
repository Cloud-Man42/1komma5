import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("renders primary variant", () => {
    render(<Button>Spara</Button>);
    expect(screen.getByRole("button", { name: "Spara" })).toHaveClass("admin-btn-primary");
  });

  it("handles click", () => {
    const onClick = vi.fn();
    render(
      <Button variant="danger" onClick={onClick}>
        Ta bort
      </Button>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Ta bort" }));
    expect(onClick).toHaveBeenCalled();
  });
});
