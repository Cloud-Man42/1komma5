import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DisplayLayout from "./layout";

describe("DisplayLayout", () => {
  it("renders its children", () => {
    const { getByText } = render(
      <DisplayLayout>
        <div className="pi-viewport">content</div>
      </DisplayLayout>,
    );
    expect(getByText("content")).toBeTruthy();
  });

  it("pins the kiosk to the dark theme", () => {
    const { container } = render(
      <DisplayLayout>
        <div>content</div>
      </DisplayLayout>,
    );
    expect(container.querySelector("[data-theme='dark']")).not.toBeNull();
  });

  it("sends the panel the dashboard's own colours", () => {
    /*
     * The first Pi mixed its output channels — red showed as magenta, green as
     * cyan, blue as yellow — and the dashboard pre-inverted that mix with an
     * feColorMatrix. The fault moved with the Pi, not the panel, so replacing
     * the board removed the need for it. Any filter here would now invert
     * correct colours.
     */
    const { container } = render(
      <DisplayLayout>
        <div className="pi-viewport">content</div>
      </DisplayLayout>,
    );
    expect(container.querySelector("filter")).toBeNull();
    expect(container.querySelector("feColorMatrix")).toBeNull();
  });
});
