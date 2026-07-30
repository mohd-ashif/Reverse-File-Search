import { useAuthStore } from "@/store/authStore";
import type { User } from "@/types/user";

/**
 * Thin convenience wrapper around `authStore`. Trivial one-line hook, added
 * per the original folder-structure spec's `hooks/useCurrentUser.ts` —
 * existing call sites reading `useAuthStore` directly are untouched; they can
 * adopt this opportunistically.
 */
export function useCurrentUser(): User | null {
  return useAuthStore((s) => s.user);
}
