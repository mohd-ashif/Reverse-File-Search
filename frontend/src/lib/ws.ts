import { API_BASE_URL } from "@/api/client";

/** Builds a ws(s):// URL for `path` relative to the same API the app talks to over HTTP. */
export function buildWsUrl(path: string): string {
  if (/^https?:\/\//.test(API_BASE_URL)) {
    return `${API_BASE_URL.replace(/^http/, "ws")}${path}`;
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const base = API_BASE_URL.startsWith("/") ? API_BASE_URL : `/${API_BASE_URL}`;
  return `${protocol}//${window.location.host}${base}${path}`;
}
