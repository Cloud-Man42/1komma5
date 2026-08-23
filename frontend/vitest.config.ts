/// <reference types="vitest" />
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  // `oxc` is Vite 8's replacement for the now-deprecated top-level `esbuild`
  // transform option (issue #49). The migration is not a rename: `oxc.jsx` is
  // typed `"preserve" | JsxOptions`, where `JsxOptions.runtime` is
  // `"classic" | "automatic"` -- so the object below, not the bare string
  // `"automatic"` that `esbuild.jsx` took.
  //
  // Do not "simplify" this to `jsx: "automatic"`. Measured: that spelling
  // still runs the whole suite green, because `JsxOptions.runtime` already
  // defaults to `"automatic"`, so the ignored value happens to coincide with
  // the default today -- no error, no warning, nothing to notice. Only `tsc`
  // reports it (TS2769, "No overload matches this call"), and `npm run
  // typecheck` already exits non-zero on four unrelated known diagnostics
  // (issue #55), so a fifth one here is easy to miss. That the JSX transform
  // is genuinely driven by this key was verified separately, by setting
  // `jsx: "preserve"` and watching 27 of 50 test files fail to parse.
  //
  // Do not "simplify" back to `esbuild` either: the `oxc` key only exists
  // from vite 8 onward, and vite is a transitive dependency here (pulled in
  // by vitest, never declared in package.json), so the version that decides
  // whether this key is understood is not readable from this file at all --
  // it is pinned by `frontend/package-lock.json`'s
  // packages["node_modules/vite"].version, which issue #49 moved from
  // 5.4.21 to 8.2.2.
  oxc: {
    jsx: {
      runtime: "automatic",
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
    },
  },
});
