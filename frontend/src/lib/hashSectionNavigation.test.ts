import { describe, expect, it, vi } from "vitest";
import {
  createSectionNavigation,
  navigateToHashHref,
  readLocationHash,
  SECTION_HASH_EVENT,
} from "./hashSectionNavigation";

describe("hashSectionNavigation", () => {
  it("reads hash from location.href after pushState", () => {
    window.history.replaceState(null, "", "/sites/akarp/energy#historik");
    expect(readLocationHash()).toBe("#historik");
  });

  it("navigateToHashHref updates url and notifies listeners", () => {
    window.history.replaceState(null, "", "/sites/akarp/solar");
    const pushState = vi.spyOn(window.history, "pushState").mockImplementation((_state, _title, url) => {
      if (typeof url === "string") {
        window.history.replaceState(_state, _title, url);
      }
    });
    const hashListener = vi.fn();
    const customListener = vi.fn();
    window.addEventListener("hashchange", hashListener);
    window.addEventListener(SECTION_HASH_EVENT, customListener);

    navigateToHashHref("/sites/akarp/solar#prognos");

    expect(pushState).toHaveBeenCalledWith(null, "", "/sites/akarp/solar#prognos");
    expect(hashListener).toHaveBeenCalledTimes(1);
    expect(customListener).toHaveBeenCalledTimes(1);
    expect(readLocationHash()).toBe("#prognos");

    pushState.mockRestore();
    window.removeEventListener("hashchange", hashListener);
    window.removeEventListener(SECTION_HASH_EVENT, customListener);
  });
});

describe("createSectionNavigation", () => {
  type TestSection = "home" | "detail";

  const nav = createSectionNavigation<TestSection>({
    defaultSection: "home",
    pathname: (slug) => `/sites/${slug}/test`,
    sectionHash: { home: "", detail: "detalj" },
    sectionLabels: { home: "Home", detail: "Detail" },
    sidebarOrder: ["home", "detail"],
  });

  it("parses hash and builds hrefs", () => {
    expect(nav.parseSection("#detalj")).toBe("detail");
    expect(nav.parseSection("#unknown")).toBe("home");
    expect(nav.sectionHref("akarp", "home")).toBe("/sites/akarp/test");
    expect(nav.sectionHref("akarp", "detail")).toBe("/sites/akarp/test#detalj");
  });

  it("builds sidebar subnav from order", () => {
    expect(nav.sidebarSubnav).toHaveLength(2);
    expect(nav.sidebarSubnav[1]?.href("akarp")).toBe("/sites/akarp/test#detalj");
  });

  it("navigateSection updates location", () => {
    window.history.replaceState(null, "", "/sites/akarp/test");
    const pushState = vi.spyOn(window.history, "pushState").mockImplementation((_state, _title, url) => {
      if (typeof url === "string") {
        window.history.replaceState(_state, _title, url);
      }
    });

    nav.navigateSection("akarp", "detail");

    expect(pushState).toHaveBeenCalledWith(null, "", "/sites/akarp/test#detalj");
    expect(nav.readSectionFromLocation()).toBe("detail");

    pushState.mockRestore();
  });

  it("supports custom isSectionActive logic", () => {
    const custom = createSectionNavigation<TestSection>({
      defaultSection: "home",
      pathname: (slug) => `/sites/${slug}/test`,
      sectionHash: { home: "", detail: "detalj" },
      sectionLabels: { home: "Home", detail: "Detail" },
      sidebarOrder: ["home"],
      isSectionActive: (_pathname, _slug, section) => section === "home",
    });

    expect(custom.isSectionActive("/other", "akarp", "home", "")).toBe(true);
    expect(custom.isSectionActive("/other", "akarp", "detail", "#detalj")).toBe(false);
  });
});
