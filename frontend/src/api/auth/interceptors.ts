import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

import { API_BASE_URL, parseError } from "@/api/client";
import { applyAuthResponse, clearAuthState } from "@/hooks/useAuth";
import { useAuthStore } from "@/store/authStore";
import type { AuthResponse } from "@/types/auth";

/**
 * A bare, interceptor-free axios instance used ONLY for the `/auth/refresh`
 * call itself. Using the main `authAxios` instance here would re-enter this
 * same response interceptor recursively on a failed refresh.
 */
const refreshAxios = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "X-Requested-With": "XMLHttpRequest",
  },
});

let isRefreshing = false;
let pendingQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token as string);
    }
  });
  pendingQueue = [];
}

function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false;
  return url.includes("/auth/refresh") || url.includes("/auth/login");
}

/**
 * Render's free tier occasionally drops the CORS preflight for `/auth/login`
 * and `/auth/refresh` outright (cold start / single worker under load), which
 * surfaces to axios as a response-less network error rather than a real
 * status code. Retrying once after a short delay clears it without the user
 * seeing an error for what is actually a transient infra hiccup.
 */
function isRetryableNetworkError(error: AxiosError): boolean {
  return !error.response;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Single-flight refresh of the access token via the httpOnly refresh cookie.
 *
 * This is the ONE shared refresh code path in the app: the axios response
 * interceptor below calls it on a 401, and `useScanSocket` (the WS hook)
 * calls it directly on a `4401`/`4403` close code, so there is exactly one
 * mutex/queue implementation rather than two independent ones.
 *
 * Concurrent callers while a refresh is already in flight are queued and all
 * resolve/reject together with the single in-flight attempt's outcome.
 */
export function refreshAccessToken(): Promise<string> {
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      pendingQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;
  return refreshAxios
    .post<AuthResponse>("/auth/refresh")
    .then(({ data }) => {
      applyAuthResponse(data);
      processQueue(null, data.accessToken);
      return data.accessToken;
    })
    .catch((refreshError) => {
      clearAuthState();
      processQueue(refreshError, null);
      throw refreshError;
    })
    .finally(() => {
      isRefreshing = false;
    });
}

/**
 * Attaches the request (bearer token) and response (401 refresh-queue)
 * interceptors to the given axios instance. Called once, from `axios.ts`,
 * right after the instance is created — kept as a function taking the
 * instance as a parameter (rather than importing the instance here) so this
 * module never imports `axios.ts`, avoiding a circular import between the
 * two files.
 */
export function attachInterceptors(instance: AxiosInstance): void {
  instance.interceptors.request.use((config) => {
    const { accessToken } = useAuthStore.getState();
    if (accessToken) {
      config.headers.set("Authorization", `Bearer ${accessToken}`);
    }
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalConfig = error.config as
        | (InternalAxiosRequestConfig & { _retry?: boolean; _networkRetry?: boolean })
        | undefined;

      if (
        originalConfig &&
        isAuthEndpoint(originalConfig.url) &&
        isRetryableNetworkError(error) &&
        !originalConfig._networkRetry
      ) {
        originalConfig._networkRetry = true;
        await delay(1000);
        return instance(originalConfig);
      }

      if (error.response?.status !== 401 || !originalConfig || isAuthEndpoint(originalConfig.url)) {
        return Promise.reject(parseError(error));
      }

      if (originalConfig._retry) {
        // Already retried once after a refresh; don't loop forever.
        return Promise.reject(parseError(error));
      }
      originalConfig._retry = true;

      try {
        const token = await refreshAccessToken();
        originalConfig.headers.set("Authorization", `Bearer ${token}`);
        return await instance(originalConfig);
      } catch {
        if (typeof window !== "undefined") {
          window.location.assign("/login");
        }
        return Promise.reject(parseError(error));
      }
    }
  );
}
