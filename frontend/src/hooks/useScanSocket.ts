import { useEffect, useRef, useState } from "react";

import { refreshAccessToken } from "@/api/auth/interceptors";
import { buildWsUrl } from "@/lib/ws";
import { useAuthStore } from "@/store/authStore";
import type { ScanSocketEvent, ScanStage, ScanSummaryEvent } from "@/types/scan";

/** Close codes the backend uses when the WS auth check fails (see `/ws/scan/{scan_id}`). */
const WS_UNAUTHORIZED_CODE = 4401;
const WS_FORBIDDEN_CODE = 4403;

export type ScanSocketStatus = "connecting" | "running" | "done" | "error";

export interface ScanSocketState {
  status: ScanSocketStatus;
  stage: ScanStage | null;
  currentFile: string | null;
  filesProcessed: number;
  filesTotal: number;
  filesRemaining: number;
  elapsedSeconds: number;
  estimatedRemainingSeconds: number | null;
  summary: ScanSummaryEvent | null;
  errorMessage: string | null;
}

const INITIAL_STATE: ScanSocketState = {
  status: "connecting",
  stage: null,
  currentFile: null,
  filesProcessed: 0,
  filesTotal: 0,
  filesRemaining: 0,
  elapsedSeconds: 0,
  estimatedRemainingSeconds: null,
  summary: null,
  errorMessage: null,
};

/** Subscribes to `/ws/scan/{scanId}` and tracks live stage/progress/summary state. */
export function useScanSocket(scanId: string | null): ScanSocketState {
  const [state, setState] = useState<ScanSocketState>(INITIAL_STATE);
  const scanIdRef = useRef<string | null>(null);
  const accessToken = useAuthStore((s) => s.accessToken);

  useEffect(() => {
    if (!scanId) {
      setState(INITIAL_STATE);
      return;
    }

    scanIdRef.current = scanId;
    setState({ ...INITIAL_STATE, status: "connecting" });

    // Guards against the isolated one-shot 4401/4403 recovery below looping
    // forever, and against a late close/message firing after cleanup.
    let didAttemptRecovery = false;
    let cancelled = false;
    let socket: WebSocket;

    function attachHandlers(ws: WebSocket) {
      ws.onopen = () => {
        if (cancelled) return;
        setState((prev) => (prev.status === "done" || prev.status === "error" ? prev : { ...prev, status: "running" }));
      };

      ws.onmessage = (event: MessageEvent<string>) => {
        if (cancelled) return;
        let payload: ScanSocketEvent;
        try {
          payload = JSON.parse(event.data) as ScanSocketEvent;
        } catch {
          return;
        }

        if (payload.type === "progress") {
          setState((prev) => ({
            ...prev,
            status: "running",
            stage: payload.stage,
            currentFile: payload.current_file,
            filesProcessed: payload.files_processed,
            filesTotal: payload.files_total,
            filesRemaining: payload.files_remaining,
            elapsedSeconds: payload.elapsed_seconds,
            estimatedRemainingSeconds: payload.estimated_remaining_seconds,
          }));
        } else if (payload.type === "summary") {
          setState((prev) => ({
            ...prev,
            status: "done",
            currentFile: null,
            elapsedSeconds: payload.elapsed_seconds,
            summary: payload,
          }));
        } else if (payload.type === "error") {
          setState((prev) => ({
            ...prev,
            status: "error",
            errorMessage: payload.message,
            elapsedSeconds: payload.elapsed_seconds,
          }));
        }
      };

      ws.onerror = () => {
        if (cancelled) return;
        setState((prev) =>
          prev.status === "done" ? prev : { ...prev, status: "error", errorMessage: prev.errorMessage ?? "Connection lost." }
        );
      };

      ws.onclose = (event: CloseEvent) => {
        if (cancelled) return;

        const isAuthFailure = event.code === WS_UNAUTHORIZED_CODE || event.code === WS_FORBIDDEN_CODE;
        if (!isAuthFailure) {
          // Normal closure (unmount cleanup, or the server closing after the
          // scan finishes) — no special handling, existing behavior stands.
          return;
        }

        if (didAttemptRecovery) {
          // Already tried a refresh+reconnect once; don't loop.
          setState((prev) => ({
            ...prev,
            status: "error",
            errorMessage: "Your session has expired. Please log in again.",
          }));
          return;
        }
        didAttemptRecovery = true;

        // Don't bother refreshing right after an intentional logout — the
        // user isn't supposed to be authenticated at all right now, so a
        // refresh attempt here would just be pointless extra work.
        if (useAuthStore.getState().status === "unauthenticated") {
          setState((prev) => ({
            ...prev,
            status: "error",
            errorMessage: "Your session has expired. Please log in again.",
          }));
          return;
        }

        void refreshAccessToken()
          .then((newToken) => {
            if (cancelled) return;
            socket = new WebSocket(buildWsUrl(`/ws/scan/${scanId}`, newToken));
            attachHandlers(socket);
          })
          .catch(() => {
            if (cancelled) return;
            setState((prev) => ({
              ...prev,
              status: "error",
              errorMessage: "Your session has expired. Please log in again.",
            }));
          });
      };
    }

    socket = new WebSocket(buildWsUrl(`/ws/scan/${scanId}`, accessToken));
    attachHandlers(socket);

    return () => {
      cancelled = true;
      socket.close();
    };
  }, [scanId, accessToken]);

  return state;
}
