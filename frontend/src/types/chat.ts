import type { SearchResultItem } from "@/types/search";

export type ChatTurnStatus = "connecting" | "streaming" | "done" | "error" | "cancelled";

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: number;
  /** Only set on assistant turns. */
  status?: ChatTurnStatus;
  sources?: string[];
  confidence?: number;
  errorMessage?: string | null;
  /** Retrieved chunks backing this answer, kept for citation lookups (file id by filename). */
  results?: SearchResultItem[];
  /** The query actually embedded for retrieval, after Groq's query-rewrite step. */
  rewrittenQuery?: string;
}
