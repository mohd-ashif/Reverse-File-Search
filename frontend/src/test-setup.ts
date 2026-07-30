import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

import "@testing-library/jest-dom/vitest";

// `vitest.config.ts` does not set `test.globals: true`, so
// `@testing-library/react`'s built-in auto-cleanup (which relies on a global
// `afterEach`) never registers on its own — wire it up explicitly here so
// each test's rendered tree is unmounted before the next test runs.
afterEach(() => {
  cleanup();
});
