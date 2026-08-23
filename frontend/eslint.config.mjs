// ESLint flat configuration for the frontend (issue #23).
//
// Why flat config: Next.js 15.5.23 (the version pinned here) supports
// `eslint.config.*`, and ESLint 9 treats it as the default format.
//
// Why FlatCompat: `eslint-config-next@15.5.23` still ships only legacy
// (eslintrc-style) shareable configs -- its package.json declares no
// `exports` field and its entry points (`index.js`, `core-web-vitals.js`,
// `typescript.js`) export plain `{ extends, rules, ... }` objects. Until
// upstream publishes a flat config, `FlatCompat` from `@eslint/eslintrc` is
// the supported bridge and is what `create-next-app` itself generates.
//
// Why ESLint 9 and not 10: `eslint-config-next@15.5.23` declares the peer
// range `^7.23.0 || ^8.0.0 || ^9.0.0`. Moving to ESLint 10 would require
// `eslint-config-next@16`, i.e. a Next.js major upgrade -- out of scope here.
//
// Ruleset: `next/core-web-vitals` + `next/typescript`, which is exactly what
// `create-next-app` generates for a TypeScript project. Both are Next's own
// recommendation and neither adds a dependency beyond `eslint-config-next`,
// which already depends on `@typescript-eslint/*`. No rule is downgraded or
// disabled: everything these presets report stays visible.

import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({
  baseDirectory: dirname(fileURLToPath(import.meta.url)),
});

const config = [
  {
    // `node_modules/` and `.git/` are ignored by flat config out of the box.
    // These are this project's own generated/build outputs.
    ignores: [".next/**", "coverage/**", "next-env.d.ts"],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default config;
