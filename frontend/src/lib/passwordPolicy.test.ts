import { describe, expect, it } from "vitest";
import { passwordPolicyChecks, validatePasswordPolicy } from "@/lib/passwordPolicy";

describe("passwordPolicy", () => {
  it("accepts short non-empty passwords", () => {
    expect(validatePasswordPolicy("abc")).toBeNull();
    expect(passwordPolicyChecks("abc").nonEmpty).toBe(true);
  });

  it("rejects empty passwords", () => {
    expect(validatePasswordPolicy("")).toBe("Lösenordet får inte vara tomt.");
    expect(validatePasswordPolicy("   ")).toBe("Lösenordet får inte vara tomt.");
  });
});
