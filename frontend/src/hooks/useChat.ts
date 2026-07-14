import { useCallback, useRef, useState } from "react";

import { API_BASE_URL } from "@/api/client";
import { parseSseStream } from "@/lib/sse";
import type { ChatTurn } from "@/types/chat";
import type { ChatMessage, SearchStreamEvent } from "@/types/search";

const DEFAULT_TOP_K = 10;
const MAX_HISTORY_MESSAGES = 20;

function makeId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** Only completed turns are sent as context — an in-progress, errored, or
 * cancelled assistant turn has no reliable content worth showing the model. */
function toHistory(turns: ChatTurn[]): ChatMessage[] {
  return turns
    .filter((turn) => turn.role === "user" || turn.status === "done")
    .slice(-MAX_HISTORY_MESSAGES)
    .map((turn) => ({ role: turn.role, content: turn.content }));
}

/** Multi-turn chat over the streaming `/search/stream` endpoint. Keeps a plain
 * ref mirror of the turn list so sendMessage/retryTurn can read the latest
 * state synchronously and fire their network side effect exactly once,
 * instead of doing it from inside a setState updater (which React may
 * invoke more than once, e.g. under StrictMode). */
export function useChat() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const turnsRef = useRef<ChatTurn[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const commitTurns = useCallback((updater: (prev: ChatTurn[]) => ChatTurn[]) => {
    setTurns((prev) => {
      const next = updater(prev);
      turnsRef.current = next;
      return next;
    });
  }, []);

  const updateTurn = useCallback(
    (id: string, patch: Partial<ChatTurn> | ((prev: ChatTurn) => Partial<ChatTurn>)) => {
      commitTurns((prev) =>
        prev.map((turn) => {
          if (turn.id !== id) return turn;
          const nextPatch = typeof patch === "function" ? patch(turn) : patch;
          return { ...turn, ...nextPatch };
        })
      );
    },
    [commitTurns]
  );

  const streamInto = useCallback(
    async (assistantId: string, query: string, history: ChatMessage[]) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(`${API_BASE_URL}/search/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, top_k: DEFAULT_TOP_K, history }),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Request failed (${response.status})`);
        }

        for await (const event of parseSseStream<SearchStreamEvent>(response)) {
          switch (event.type) {



            case "query":
              updateTurn(assistantId, { rewrittenQuery: event.rewritten_query });
              break;
            case "results":
              updateTurn(assistantId, { results: event.results });
              break;
            case "meta":
              updateTurn(assistantId, {
                status: "streaming",
                sources: event.sources,
                confidence: event.confidence,
              });
              break;
            case "token":
              updateTurn(assistantId, (prev) => ({
                status: "streaming",
                content: prev.content + event.text,
              }));
              break;
            case "error":
              updateTurn(assistantId, { status: "error", errorMessage: event.message });
              break;
            case "done":
              updateTurn(assistantId, { status: "done" });
              break;
          }
        }
      } catch (error) {
        if (controller.signal.aborted) {
          updateTurn(assistantId, { status: "cancelled" });
          return;
        }
        updateTurn(assistantId, {
          status: "error",
          errorMessage: error instanceof Error ? error.message : "Something went wrong.",
        });
      }
    },
    [updateTurn]
  );

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      const history = toHistory(turnsRef.current);
      const userTurn: ChatTurn = { id: makeId(), role: "user", content: trimmed, createdAt: Date.now() };
      const assistantId = makeId();
      const assistantTurn: ChatTurn = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: Date.now(),
        status: "connecting",
      };

      commitTurns((prev) => [...prev, userTurn, assistantTurn]);
      void streamInto(assistantId, trimmed, history);
    },
    [commitTurns, streamInto]
  );

  const retryTurn = useCallback(
    (assistantId: string) => {
      const prev = turnsRef.current;
      const index = prev.findIndex((turn) => turn.id === assistantId);
      if (index <= 0) return;
      const userTurn = prev[index - 1];
      if (userTurn.role !== "user") return;

      const history = toHistory(prev.slice(0, index - 1));

      commitTurns((current) =>
        current.map((turn) =>
          turn.id === assistantId
            ? {
                ...turn,
                content: "",
                status: "connecting" as const,
                errorMessage: null,
                sources: undefined,
                confidence: undefined,
                rewrittenQuery: undefined,
              }
            : turn
        )
      );
      void streamInto(assistantId, userTurn.content, history);
    },
    [commitTurns, streamInto]
  );

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clear = useCallback(() => {
    abortRef.current?.abort();
    commitTurns(() => []);
  }, [commitTurns]);

  const isStreaming = turns.some((turn) => turn.status === "connecting" || turn.status === "streaming");

  return { turns, sendMessage, retryTurn, cancel, clear, isStreaming };
}
