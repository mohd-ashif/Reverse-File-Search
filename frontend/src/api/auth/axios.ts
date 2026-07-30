import axios from "axios";

import { API_BASE_URL } from "@/api/client";
import { attachInterceptors } from "@/api/auth/interceptors";

/**
 * The single axios instance used by the whole app (folders/files/search/auth).
 * `withCredentials: true` so the httpOnly `refresh_token` cookie (scoped to
 * `/api/v1/auth`) is sent on requests that need it.
 *
 * Interceptor attachment lives in `interceptors.ts` and is invoked here (once,
 * at module-init time) rather than the other way around, so `interceptors.ts`
 * never needs to import this module — it only receives the instance as a
 * function argument. That keeps the dependency graph a-cyclic:
 * `axios.ts -> interceptors.ts`, never the reverse.
 */
export const authAxios = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30_000,
  withCredentials: true,
});

attachInterceptors(authAxios);
