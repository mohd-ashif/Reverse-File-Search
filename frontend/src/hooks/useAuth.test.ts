import { describe, expect, it } from "vitest";

import { applyAuthResponse, clearAuthState } from "@/hooks/useAuth";
import { useAuthStore } from "@/store/authStore";
import { useOrganizationStore } from "@/store/organizationStore";
import { usePermissionStore } from "@/store/permissionStore";
import { useRoleStore } from "@/store/roleStore";
import type { AuthResponse } from "@/types/auth";

const fakeAuthResponse: AuthResponse = {
  accessToken: "fake-access-token",
  refreshToken: "fake-refresh-token",
  expiresIn: 900,
  user: {
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
  },
  permissions: ["folder.read", "file.read", "search.execute"],
  roles: ["Employee"],
  organization: { id: 1, name: "Acme", slug: "acme" },
};

describe("applyAuthResponse / clearAuthState", () => {
  it("populates all three stores atomically", () => {
    applyAuthResponse(fakeAuthResponse);

    expect(useAuthStore.getState().user).toEqual(fakeAuthResponse.user);
    expect(useAuthStore.getState().accessToken).toBe("fake-access-token");
    expect(useAuthStore.getState().status).toBe("authenticated");
    expect(usePermissionStore.getState().permissions).toEqual([
      "folder.read",
      "file.read",
      "search.execute",
    ]);
    expect(useOrganizationStore.getState().organization).toEqual({
      id: 1,
      name: "Acme",
      slug: "acme",
    });
    expect(useRoleStore.getState().roles).toEqual(["Employee"]);
  });

  it("clears all four stores atomically", () => {
    applyAuthResponse(fakeAuthResponse);
    clearAuthState();

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().status).toBe("unauthenticated");
    expect(usePermissionStore.getState().permissions).toEqual([]);
    expect(useOrganizationStore.getState().organization).toBeNull();
    expect(useRoleStore.getState().roles).toEqual([]);
  });

  it("honors a null organization in the response rather than leaving a stale one", () => {
    // First populate with an organization, then apply a second response that
    // has none (e.g. a user removed from their org) — the store must actually
    // be overwritten to null, not skipped/left stale.
    applyAuthResponse(fakeAuthResponse);
    expect(useOrganizationStore.getState().organization).not.toBeNull();

    applyAuthResponse({ ...fakeAuthResponse, organization: null });
    expect(useOrganizationStore.getState().organization).toBeNull();
    // The other two stores are unaffected by that change and remain populated.
    expect(useAuthStore.getState().user).toEqual(fakeAuthResponse.user);
    expect(usePermissionStore.getState().permissions).toEqual(fakeAuthResponse.permissions);
  });

  it("applyAuthResponse only touches user/accessToken/status on authStore, not e.g. re-deriving other fields", () => {
    applyAuthResponse(fakeAuthResponse);
    const afterFirst = useAuthStore.getState();

    // Re-applying the same response should leave the store shape identical
    // (no stray fields introduced, no accidental partial overwrite).
    applyAuthResponse(fakeAuthResponse);
    const afterSecond = useAuthStore.getState();

    expect(Object.keys(afterSecond).sort()).toEqual(Object.keys(afterFirst).sort());
    expect(afterSecond.user).toEqual(afterFirst.user);
    expect(afterSecond.accessToken).toBe(afterFirst.accessToken);
    expect(afterSecond.status).toBe(afterFirst.status);
  });
});
