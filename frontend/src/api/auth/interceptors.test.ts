import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AuthResponse } from "@/types/auth";

/**
 * Testing strategy: `interceptors.ts` creates its own internal, unexported
 * `refreshAxios` instance via `axios.create(...)` at module-load time, so we
 * cannot get a handle to it directly to attach a mock adapter to it
 * specifically. Instead we lean on a real axios-mock-adapter behavior: when
 * `new MockAdapter(axios)` is constructed against the top-level default
 * `axios` export, it sets `axios.defaults.adapter` to the mock's adapter
 * function. Any axios instance subsequently created via `axios.create(...)`
 * merges its config against `axios.defaults`, and since `adapter` isn't
 * overridden by `axios.create()`'s own (empty) instance config, it inherits
 * that same mock adapter. That means ONE MockAdapter, constructed on the
 * bare `axios` import *before* `interceptors.ts` is (re-)imported, ends up
 * transparently intercepting both the internal `refreshAxios` instance and
 * whatever instance we attach `attachInterceptors` to in the test, without
 * needing to export `refreshAxios` from the real module.
 *
 * This requires `vi.resetModules()` plus dynamic `import()` in each test so
 * that module-load-time `axios.create()` calls happen *after* the mock
 * adapter is wired up, and so each test gets an isolated module graph (fresh
 * `isRefreshing`/`pendingQueue` closures in `interceptors.ts`, fresh store
 * instances).
 */

const fakeUser = {
  id: 1,
  email: "test@example.com",
  full_name: "Test User",
  first_name: "Test",
  last_name: "User",
  avatar_url: null,
  phone: null,
  is_active: true,
  is_verified: true,
  last_login_at: null,
  created_at: "2026-01-01T00:00:00Z",
};

const refreshedAuthResponse: AuthResponse = {
  accessToken: "new-token",
  refreshToken: "new-refresh-token",
  expiresIn: 900,
  user: fakeUser,
  permissions: ["folder.read"],
  roles: ["Employee"],
  organization: null,
};

async function setupHarness() {
  vi.resetModules();

  const axiosModule = await import("axios");
  const axios = axiosModule.default;
  const { default: MockAdapter } = await import("axios-mock-adapter");

  // Attached to the bare `axios` export BEFORE interceptors.ts (and its
  // internal `axios.create()` call for `refreshAxios`) is imported below, so
  // that internal instance inherits this same mock adapter (see file-level
  // comment).
  const mock = new MockAdapter(axios);

  const { attachInterceptors } = await import("@/api/auth/interceptors");
  const { useAuthStore } = await import("@/store/authStore");

  const testInstance = axios.create({ baseURL: "http://test.local" });
  attachInterceptors(testInstance);

  return { axios, mock, testInstance, useAuthStore };
}

describe("auth response interceptor (401 refresh-queue)", () => {
  let harness: Awaited<ReturnType<typeof setupHarness>>;
  let assignSpy: ReturnType<typeof vi.fn>;
  const originalLocation = window.location;

  beforeEach(async () => {
    harness = await setupHarness();
    // jsdom's window.location.assign is non-configurable on the real Location
    // object, so vi.spyOn can't redefine it directly — swap the whole
    // `window.location` for a plain stub object instead.
    assignSpy = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...originalLocation, assign: assignSpy },
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    harness.mock.restore();
    Object.defineProperty(window, "location", {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
  });

  it("retries a single 401'd request after exactly one refresh call, and it succeeds", async () => {
    const { mock, testInstance } = harness;

    mock.onPost("/auth/refresh").reply(200, refreshedAuthResponse);
    mock.onGet("/protected").reply((config) => {
      if (config.headers?.Authorization === "Bearer new-token") {
        return [200, { ok: true }];
      }
      return [401];
    });

    const response = await testInstance.get("/protected");

    expect(response.status).toBe(200);
    expect(response.data).toEqual({ ok: true });
    expect(mock.history.post.filter((r) => r.url === "/auth/refresh")).toHaveLength(1);
  });

  it("collapses three concurrent 401s into exactly one refresh call, and all three retries resolve", async () => {
    const { mock, testInstance } = harness;

    mock.onPost("/auth/refresh").reply(200, refreshedAuthResponse);
    mock.onGet("/protected").reply((config) => {
      if (config.headers?.Authorization === "Bearer new-token") {
        return [200, { ok: true }];
      }
      return [401];
    });

    const results = await Promise.all([
      testInstance.get("/protected"),
      testInstance.get("/protected"),
      testInstance.get("/protected"),
    ]);

    for (const response of results) {
      expect(response.status).toBe(200);
      expect(response.data).toEqual({ ok: true });
    }
    expect(mock.history.post.filter((r) => r.url === "/auth/refresh")).toHaveLength(1);
  });

  it("rejects all queued requests and clears auth state + redirects when the refresh call itself fails", async () => {
    const { mock, testInstance, useAuthStore } = harness;

    useAuthStore.getState().setSession(fakeUser, "stale-token");
    useAuthStore.getState().setStatus("authenticated");

    mock.onPost("/auth/refresh").reply(401);
    mock.onGet("/protected").reply(401);

    const outcomes = await Promise.allSettled([
      testInstance.get("/protected"),
      testInstance.get("/protected"),
    ]);

    for (const outcome of outcomes) {
      expect(outcome.status).toBe("rejected");
    }
    // Refresh is single-flight even on failure: only attempted once for both
    // concurrent callers.
    expect(mock.history.post.filter((r) => r.url === "/auth/refresh")).toHaveLength(1);

    // clearAuthState()-equivalent behavior: authStore wiped back to
    // unauthenticated.
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().status).toBe("unauthenticated");

    // Hard redirect to /login on refresh failure.
    expect(assignSpy).toHaveBeenCalledWith("/login");
  });

  it("does not attempt a refresh for a 401 returned by /auth/login itself", async () => {
    const { mock, testInstance } = harness;

    mock.onPost("/auth/refresh").reply(200, refreshedAuthResponse);
    mock.onPost("/auth/login").reply(401, { detail: "Invalid credentials" });

    await expect(
      testInstance.post("/auth/login", { email: "a@b.com", password: "wrong" })
    ).rejects.toThrow();

    expect(mock.history.post.filter((r) => r.url === "/auth/refresh")).toHaveLength(0);
    expect(assignSpy).not.toHaveBeenCalled();
  });
});
