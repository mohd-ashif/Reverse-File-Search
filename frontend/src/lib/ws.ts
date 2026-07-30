import { API_BASE_URL } from "@/api/client";

/**
 * Builds a ws(s):// URL for `path` relative to the same API the app talks to
 * over HTTP, appending `token` as a `?token=` query param (as required by the
 * backend's `/ws/scan/{scan_id}` auth check) when one is provided.
 */
export function buildWsUrl(path: string, token: string | null): string {
  let base: string;
  if (/^https?:\/\//.test(API_BASE_URL)) {
    base = `${API_BASE_URL.replace(/^http/, "ws")}${path}`;
  } else {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const prefixed = API_BASE_URL.startsWith("/") ? API_BASE_URL : `/${API_BASE_URL}`;
    base = `${protocol}//${window.location.host}${prefixed}${path}`;
  }
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}
