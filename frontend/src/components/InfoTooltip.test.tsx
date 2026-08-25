import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InfoTooltip } from "./InfoTooltip";

describe("InfoTooltip", () => {
  it("renders label and tooltip text", () => {
    render(
      <dl>
        <InfoTooltip label="Solen har sparat" text="Beräknad kostnad för solel." />
      </dl>,
    );

    const term = screen.getByText("Solen har sparat");
    expect(term.getAttribute("title")).toBe("Beräknad kostnad för solel.");
    expect(term.getAttribute("aria-label")).toBe("Solen har sparat. Beräknad kostnad för solel.");
  });
});
