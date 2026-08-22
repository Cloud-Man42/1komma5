import { describe, expect, it } from "vitest";

import { render, waitFor } from "@testing-library/react";

import { WireFlowPulse } from "./WireFlowPulse";



describe("WireFlowPulse", () => {

  it("renders a dim track and scrolling dash layers for active flow", async () => {

    render(

      <svg viewBox="0 0 100 67">

        <WireFlowPulse path="M 10 10 L 90 10" watts={1500} kind="solar" />

      </svg>,

    );

    await waitFor(() => {

      expect(document.querySelector(".energy-wire-flow-track")).toBeTruthy();

    });

    expect(document.querySelectorAll(".energy-wire-flow-glow").length).toBe(3);

    expect(document.querySelectorAll(".energy-wire-flow-core").length).toBe(3);

  });



  it("renders nothing when flow is below threshold", () => {

    render(

      <svg viewBox="0 0 100 67">

        <WireFlowPulse path="M 10 10 L 90 10" watts={5} kind="grid-import" />

      </svg>,

    );

    expect(document.querySelector(".energy-wire-flow-track")).toBeNull();

  });

});


