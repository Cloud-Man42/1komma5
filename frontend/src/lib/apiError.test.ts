import { describe, expect, it } from "vitest";
import { formatDependencyConflict, parseApiError } from "@/lib/apiError";

describe("parseApiError", () => {
  it("parses string detail", async () => {
    const res = new Response(JSON.stringify({ detail: "Site not found" }), { status: 404 });
    const err = await parseApiError(res);
    expect(err.status).toBe(404);
    expect(err.detail.message).toBe("Site not found");
  });

  it("parses structured dependency conflict", async () => {
    const res = new Response(
      JSON.stringify({
        detail: {
          message: "Cannot disable module",
          dependent_modules: ["feature.smart-charging"],
        },
      }),
      { status: 409 },
    );
    const err = await parseApiError(res);
    expect(err.detail.dependent_modules).toEqual(["feature.smart-charging"]);
    expect(formatDependencyConflict(err.detail, { "feature.smart-charging": "Smart Charging" })).toContain(
      "Smart Charging",
    );
  });
});
