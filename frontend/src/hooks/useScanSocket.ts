import { useEffect, useRef, useState } from "react";

import { buildWsUrl } from "@/lib/ws";
import type { ScanSocketEvent, ScanStage, ScanSummaryEvent } from "@/types/scan";

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

  useEffect(() => {
    if (!scanId) {
      setState(INITIAL_STATE);
      return;
    }

    scanIdRef.current = scanId;
    setState({ ...INITIAL_STATE, status: "connecting" });

    const socket = new WebSocket(buildWsUrl(`/ws/scan/${scanId}`));

    socket.onopen = () => {
      setState((prev) => (prev.status === "done" || prev.status === "error" ? prev : { ...prev, status: "running" }));
    };

    socket.onmessage = (event: MessageEvent<string>) => {
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

    socket.onerror = () => {
      setState((prev) =>
        prev.status === "done" ? prev : { ...prev, status: "error", errorMessage: prev.errorMessage ?? "Connection lost." }
      );
    };

    return () => {
      socket.close();
    };
  }, [scanId]);

  return state;
}
