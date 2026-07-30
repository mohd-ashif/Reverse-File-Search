import { create } from "zustand";

import type { User } from "@/types/user";

export type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  status: AuthStatus;
  setSession: (user: User, accessToken: string) => void;
  updateUser: (patch: Partial<User>) => void;
  clear: () => void;
  setStatus: (status: AuthStatus) => void;
}

/**
 * Holds the current user and the in-memory access token.
 *
 * IMPORTANT: this store is intentionally NOT wrapped in zustand's `persist`
 * middleware. The access token must never be written to localStorage /
 * sessionStorage — that's a hard security requirement, not a style choice.
 * Session continuity across page reloads is instead achieved via a silent
 * `/auth/refresh` call (which relies on the httpOnly refresh cookie) on app
 * boot.
 */
export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  status: "idle",
  setSession: (user, accessToken) => set({ user, accessToken }),
  updateUser: (patch) =>
    set((state) => ({ user: state.user ? { ...state.user, ...patch } : state.user })),
  clear: () => set({ user: null, accessToken: null }),
  setStatus: (status) => set({ status }),
}));
