import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PasswordField } from "./PasswordField";

describe("PasswordField", () => {
  it("toggles password visibility", () => {
    render(<PasswordField label="Lösenord" value="secret" onChange={() => undefined} />);
    const input = screen.getByLabelText("Lösenord");
    expect(input).toHaveAttribute("type", "password");
    fireEvent.click(screen.getByRole("button", { name: "Visa" }));
    expect(input).toHaveAttribute("type", "text");
  });
});
