export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SearchQuery {
  query: string;
  top_k?: number;
  generate_answer?: boolean;
  history?: ChatMessage[];
}

export interface SearchResultItem {
  file_id: number;
  filename: string;
  chunk_text: string | null;
  score: number | null;
}

export interface AIAnswer {
  text: string;
  sources: string[];
  confidence: number;
}

export interface SearchResponse {
  results: SearchResultItem[];
  answer: AIAnswer | null;
}

export type SearchStreamEvent =
  | { type: "results"; results: SearchResultItem[] }
  | { type: "meta"; sources: string[]; confidence: number }
  | { type: "token"; text: string }
  | { type: "done" }
  | { type: "error"; message: string };
