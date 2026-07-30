import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { useCurrentUser } from "@/hooks/useCurrentUser";
import { useAuthStore } from "@/store/authStore";
import type { User } from "@/types/user";

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

describe("useCurrentUser", () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, accessToken: null, status: "idle" });
  });

  it("returns null when no user is logged in", () => {
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current).toBeNull();
  });

  it("returns the current user from authStore", () => {
    useAuthStore.getState().setSession(fakeUser, "token-123");
    const { result } = renderHook(() => useCurrentUser());
    expect(result.current).toEqual(fakeUser);
  });
});
