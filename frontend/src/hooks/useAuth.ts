import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as authApi from "@/api/auth/authApi";
import { useAuthStore } from "@/store/authStore";
import { useOrganizationStore } from "@/store/organizationStore";
import { usePermissionStore } from "@/store/permissionStore";
import { useRoleStore } from "@/store/roleStore";
import type { AuthResponse } from "@/types/auth";

/**
 * Plain (non-hook) helpers that atomically apply/clear auth state across all
 * three stores. These are consumed both by non-React code (the axios
 * response interceptor, which has no access to React context) and — in a
 * later phase — by React Query mutations. They deliberately live outside any
 * store module so that no store needs to import another store.
 */
export function applyAuthResponse(data: AuthResponse): void {
  useAuthStore.getState().setSession(data.user, data.accessToken);
  usePermissionStore.getState().setPermissions(data.permissions);
  useRoleStore.getState().setRoles(data.roles ?? []);
  useOrganizationStore.getState().setOrganization(data.organization);
  useAuthStore.getState().setStatus("authenticated");
}

export function clearAuthState(): void {
  useAuthStore.getState().clear();
  usePermissionStore.getState().clear();
  useRoleStore.getState().clear();
  useOrganizationStore.getState().clear();
  useAuthStore.getState().setStatus("unauthenticated");
}

/**
 * React Query hooks wrapping `authApi.ts`. These follow the same
 * query-key/mutation conventions established in `hooks/useFolders.ts`
 * (plain array query keys, `queryClient.invalidateQueries({ queryKey })`).
 */

export const meQueryKey = ["me"] as const;
export const sessionsQueryKey = ["me", "sessions"] as const;

export function useLogin() {
  return useMutation({
    mutationFn: authApi.login,
    onSuccess: applyAuthResponse,
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: authApi.register,
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      clearAuthState();
      queryClient.clear();
    },
  });
}

export function useForgotPassword() {
  return useMutation({ mutationFn: authApi.forgotPassword });
}

export function useResetPassword() {
  return useMutation({ mutationFn: authApi.resetPassword });
}

export function useVerifyEmail() {
  return useMutation({ mutationFn: authApi.verifyEmail });
}

export function useResendVerification() {
  return useMutation({ mutationFn: authApi.resendVerification });
}

export function useChangePassword() {
  return useMutation({ mutationFn: authApi.changePassword });
}

export function useMe() {
  const status = useAuthStore((s) => s.status);
  return useQuery({
    queryKey: meQueryKey,
    queryFn: authApi.getMe,
    enabled: status === "authenticated",
  });
}

export function useUpdateMe() {
  return useMutation({
    mutationFn: authApi.updateMe,
    onSuccess: (user) => {
      useAuthStore.getState().updateUser(user);
    },
  });
}

export function useSessions() {
  const status = useAuthStore((s) => s.status);
  return useQuery({
    queryKey: sessionsQueryKey,
    queryFn: authApi.getSessions,
    enabled: status === "authenticated",
  });
}

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authApi.revokeSession,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionsQueryKey });
    },
  });
}

/**
 * Fires exactly once per app load: attempts a silent `/auth/refresh` using
 * the httpOnly cookie to restore a session without a visible login flash.
 *
 * On success, applies the returned session to all three stores. On failure
 * (no cookie / expired / network error) it clears state to "unauthenticated"
 * — this is an expected, silent outcome for a never-logged-in visitor, not an
 * error to surface.
 *
 * Must only run once even under React StrictMode's dev double-invoke of
 * effects, so the guard is a plain module-level flag (not component state,
 * which StrictMode intentionally discards/reinvokes) combined with a
 * per-mount ref so a second *component* mount (not just the double-effect)
 * doesn't refire either.
 */
let bootstrapStarted = false;

export function useBootstrapAuth(): void {
  useEffect(() => {
    if (bootstrapStarted) return;
    bootstrapStarted = true;

    useAuthStore.getState().setStatus("loading");

    void authApi
      .refresh()
      .then((data) => {
        applyAuthResponse(data);
      })
      .catch(() => {
        clearAuthState();
      });
    // Empty deps: run once on mount. The module-level `bootstrapStarted` flag
    // (not component state) is what actually prevents a second invocation
    // under React StrictMode's dev-mode mount->unmount->mount double effect
    // cycle, since that flag survives the unmount/remount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
