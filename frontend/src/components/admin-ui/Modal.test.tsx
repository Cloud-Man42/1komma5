import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "./Modal";

describe("Modal", () => {
  it("closes on Escape", () => {
    const onClose = vi.fn();
    render(
      <Modal open title="Test" onClose={onClose}>
        Body
      </Modal>,
    );
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("renders dialog content when open", () => {
    render(
      <Modal open title="Rubrik" onClose={() => undefined}>
        Innehåll
      </Modal>,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Innehåll")).toBeInTheDocument();
  });
});
