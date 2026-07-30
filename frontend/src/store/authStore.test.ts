import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/store/authStore";
import type { User } from "@/types/user";

const initialState = useAuthStore.getState();

const fakeUser: User = {
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

describe("authStore", () => {
  beforeEach(() => {
    useAuthStore.setState(initialState, true);
  });

  it("starts in the idle status with no user/token", () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.status).toBe("idle");
  });

  it("setSession populates user and accessToken", () => {
    useAuthStore.getState().setSession(fakeUser, "token-123");
    const state = useAuthStore.getState();
    expect(state.user).toEqual(fakeUser);
    expect(state.accessToken).toBe("token-123");
  });

  it("updateUser merges a partial patch into the existing user", () => {
    useAuthStore.getState().setSession(fakeUser, "token-123");
    useAuthStore.getState().updateUser({ full_name: "New Name" });
    expect(useAuthStore.getState().user).toEqual({ ...fakeUser, full_name: "New Name" });
    // Unrelated fields (accessToken/status) are left alone.
    expect(useAuthStore.getState().accessToken).toBe("token-123");
  });

  it("updateUser is a no-op when there is no current user", () => {
    useAuthStore.getState().updateUser({ full_name: "Nobody" });
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("setStatus transitions the status field only", () => {
    useAuthStore.getState().setSession(fakeUser, "token-123");
    useAuthStore.getState().setStatus("authenticated");
    const state = useAuthStore.getState();
    expect(state.status).toBe("authenticated");
    expect(state.user).toEqual(fakeUser);
    expect(state.accessToken).toBe("token-123");
  });

  it("clear() resets user/accessToken back to the initial unauthenticated shape", () => {
    useAuthStore.getState().setSession(fakeUser, "token-123");
    useAuthStore.getState().setStatus("authenticated");
    useAuthStore.getState().clear();
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
  });

  it("never writes the access token (or anything else) to localStorage/sessionStorage", () => {
    const localSetItem = vi.spyOn(window.localStorage.__proto__, "setItem");
    const sessionSetItem = vi.spyOn(window.sessionStorage.__proto__, "setItem");

    useAuthStore.getState().setSession(fakeUser, "super-secret-access-token");
    useAuthStore.getState().setStatus("authenticated");
    useAuthStore.getState().updateUser({ full_name: "Changed" });
    useAuthStore.getState().clear();

    expect(localSetItem).not.toHaveBeenCalled();
    expect(sessionSetItem).not.toHaveBeenCalled();
    expect(window.localStorage.getItem("super-secret-access-token")).toBeNull();

    localSetItem.mockRestore();
    sessionSetItem.mockRestore();
  });
});
