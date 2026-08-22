import { afterEach, describe, expect, it } from "vitest";

/**
 * Regression coverage for issue #11.
 *
 * Node 26 defines `localStorage` and `sessionStorage` as accessor properties
 * directly on `globalThis` (`'localStorage' in globalThis` is `true`).
 * Vitest's jsdom environment bridge only copies keys that are present in its
 * own `KEYS` allow-list onto `globalThis`; `localStorage`/`sessionStorage`
 * are not in that list, so jsdom's working `window.localStorage`
 * implementation is never wired up as the global `localStorage`. The result
 * is that `typeof localStorage === "undefined"` even though the property
 * exists, and any application code that calls `localStorage.getItem(...)`
 * (or `sessionStorage.*`) at the bare global identifier throws instead of
 * reading/writing storage.
 *
 * The tests below assert the contract that application code, and the rest
 * of this test suite, relies on: `localStorage` and `sessionStorage` are
 * reachable as bare globals and behave like a real Web Storage API.
 */
describe("test environment: Web Storage globals", () => {
  afterEach(() => {
    globalThis.localStorage?.clear();
    globalThis.sessionStorage?.clear();
  });

  describe("localStorage", () => {
    it("is defined as a working Storage instance on globalThis", () => {
      expect(globalThis.localStorage).toBeDefined();
      expect(typeof globalThis.localStorage).toBe("object");
      expect(typeof globalThis.localStorage.setItem).toBe("function");
      expect(typeof globalThis.localStorage.getItem).toBe("function");
      expect(typeof globalThis.localStorage.removeItem).toBe("function");
      expect(typeof globalThis.localStorage.clear).toBe("function");
    });

    it("is reachable as a bare, unqualified global identifier", () => {
      expect(typeof localStorage).toBe("object");
      expect(localStorage).not.toBeUndefined();
    });

    it("round-trips a value written with setItem and read with getItem", () => {
      localStorage.setItem("emic.test.key", "emic-value-123");
      expect(localStorage.getItem("emic.test.key")).toBe("emic-value-123");
    });

    it("returns null for a key that was never set", () => {
      expect(localStorage.getItem("emic.test.never-set")).toBeNull();
    });

    it("removes a single stored key when removeItem is called", () => {
      localStorage.setItem("emic.test.remove", "to-be-removed");
      localStorage.removeItem("emic.test.remove");
      expect(localStorage.getItem("emic.test.remove")).toBeNull();
    });

    it("removes all stored keys when clear is called", () => {
      localStorage.setItem("emic.test.a", "1");
      localStorage.setItem("emic.test.b", "2");
      localStorage.clear();
      expect(localStorage.getItem("emic.test.a")).toBeNull();
      expect(localStorage.getItem("emic.test.b")).toBeNull();
      expect(localStorage.length).toBe(0);
    });
  });

  describe("sessionStorage", () => {
    it("is defined as a working Storage instance on globalThis", () => {
      expect(globalThis.sessionStorage).toBeDefined();
      expect(typeof globalThis.sessionStorage).toBe("object");
      expect(typeof globalThis.sessionStorage.setItem).toBe("function");
      expect(typeof globalThis.sessionStorage.getItem).toBe("function");
      expect(typeof globalThis.sessionStorage.removeItem).toBe("function");
      expect(typeof globalThis.sessionStorage.clear).toBe("function");
    });

    it("is reachable as a bare, unqualified global identifier", () => {
      expect(typeof sessionStorage).toBe("object");
      expect(sessionStorage).not.toBeUndefined();
    });

    it("round-trips a value written with setItem and read with getItem", () => {
      sessionStorage.setItem("emic.test.key", "emic-session-value-123");
      expect(sessionStorage.getItem("emic.test.key")).toBe(
        "emic-session-value-123",
      );
    });

    it("returns null for a key that was never set", () => {
      expect(sessionStorage.getItem("emic.test.never-set")).toBeNull();
    });

    it("removes a single stored key when removeItem is called", () => {
      sessionStorage.setItem("emic.test.remove", "to-be-removed");
      sessionStorage.removeItem("emic.test.remove");
      expect(sessionStorage.getItem("emic.test.remove")).toBeNull();
    });

    it("removes all stored keys when clear is called", () => {
      sessionStorage.setItem("emic.test.a", "1");
      sessionStorage.setItem("emic.test.b", "2");
      sessionStorage.clear();
      expect(sessionStorage.getItem("emic.test.a")).toBeNull();
      expect(sessionStorage.getItem("emic.test.b")).toBeNull();
      expect(sessionStorage.length).toBe(0);
    });
  });

  it("keeps localStorage and sessionStorage as independent stores", () => {
    localStorage.setItem("emic.test.shared-key", "from-local");
    sessionStorage.setItem("emic.test.shared-key", "from-session");
    expect(localStorage.getItem("emic.test.shared-key")).toBe("from-local");
    expect(sessionStorage.getItem("emic.test.shared-key")).toBe(
      "from-session",
    );
  });
});
