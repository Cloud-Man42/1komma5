import "@testing-library/jest-dom/vitest";

/**
 * Web Storage polyfill for the jsdom test environment (issue #11).
 *
 * DO NOT REMOVE — this is not redundant with jsdom.
 *
 * Node 26 defines `localStorage` and `sessionStorage` as accessor properties
 * directly on `globalThis`, so `"localStorage" in globalThis` is already true
 * before jsdom is installed. Vitest's `populateGlobal` only copies a window
 * property onto the global when the key is absent from the global, or present
 * in its own `KEYS` allow-list; neither storage key is on that list. jsdom's
 * working implementation is therefore never wired up, and `globalThis.localStorage`
 * keeps Node's getter — which yields `undefined` unless node is started with
 * `--localstorage-file`. Application code such as `readLegacyConfigs` in
 * `src/lib/energySceneConfig.ts` then throws on the bare `localStorage`
 * identifier instead of reading storage.
 *
 * `sessionStorage` is bound here too, even though Node's getter does return a
 * working Storage. Node's instance is process-wide, so values written by one
 * test file survive into the next file that reuses the same worker process,
 * while jsdom's is created and closed per test file. Binding both keeps them
 * isolated per file and in the same realm as `globalThis.Storage`, so
 * `localStorage instanceof Storage` holds and `Storage.prototype` spies work.
 *
 * Inside vitest's jsdom environment `window`, `self` and `document.defaultView`
 * are all aliases for `globalThis`, so the real jsdom window cannot be reached
 * through them. It is reached through the `jsdom` handle that vitest assigns to
 * the global during environment setup.
 *
 * That handle is not part of vitest's public API, so its absence is treated
 * as a hard setup failure below rather than a silent skip. Covered by
 * `src/test/environment.test.ts`, which fails loudly if this binding stops
 * working.
 */
const jsdomWindow = (
  globalThis as typeof globalThis & {
    jsdom?: { window: Pick<Window, "localStorage" | "sessionStorage"> };
  }
).jsdom?.window;

// Fail the setup file loudly instead of skipping the binding. A skipped
// binding is invisible here and resurfaces as every Web Storage test in the
// suite throwing "localStorage is not defined", which points the reader at
// the application code rather than at this file. Throwing makes this file
// the reported cause, with the same message on every test file, and costs
// nothing in coverage: `vitest.config.ts` sets `environment: "jsdom"` for
// the whole suite and no test opts out via `@vitest-environment`, so a
// missing jsdom window is always a defect, never a supported setup.
if (!jsdomWindow) {
  throw new Error(
    "Web Storage polyfill for issue #11 could not install: " +
      "`globalThis.jsdom` is missing or exposes no `window`. That handle " +
      "is an internal vitest implementation detail of the jsdom " +
      "environment (assigned by `global.jsdom = dom` in vitest's jsdom " +
      "env setup), not a public API, so the likely cause is a vitest " +
      "upgrade that renamed or removed it. `frontend/package.json` " +
      "declares `\"vitest\": \"^2.1.8\"`, so a routine lockfile refresh " +
      "can pull in such a change without a major version bump. To fix: " +
      "find where the installed vitest attaches the real jsdom window to " +
      "the global and re-point `jsdomWindow` in " +
      "`frontend/src/test/setup.ts` at it. Do not delete the binding — " +
      "under Node 26 the bare `localStorage` global resolves to Node's " +
      "own accessor, which yields `undefined`.",
  );
}

for (const key of ["localStorage", "sessionStorage"] as const) {
  // Mirrors how vitest's own `populateGlobal` exposes window properties:
  // a configurable accessor that reads through to the jsdom window, but
  // still allows a test to substitute its own stub by assignment.
  let override: Storage | undefined;
  Object.defineProperty(globalThis, key, {
    configurable: true,
    get: () => override ?? jsdomWindow[key],
    set: (value: Storage) => {
      override = value;
    },
  });
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => false,
  }),
});
