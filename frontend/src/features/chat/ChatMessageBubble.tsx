import { useState } from "react";
import { AlertCircle, Bot, Check, Copy, RotateCcw, User } from "lucide-react";
import { toast } from "sonner";

import { MarkdownContent } from "@/components/common/MarkdownContent";
import { TypingIndicator } from "@/components/common/TypingIndicator";
import { SourceCitations } from "@/features/chat/SourceCitations";
import { cn } from "@/lib/utils";
import type { ChatTurn } from "@/types/chat";

interface ChatMessageBubbleProps {
  turn: ChatTurn;
  onRetry: (assistantId: string) => void;
  onSelectFile: (fileId: number) => void;
}

export function ChatMessageBubble({ turn, onRetry, onSelectFile }: ChatMessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = turn.role === "user";
  const isActive = turn.status === "connecting" || turn.status === "streaming";
  const isWaitingForFirstToken = isActive && turn.content.length === 0;
  const canRetry =
    turn.role === "assistant" && (turn.status === "done" || turn.status === "error" || turn.status === "cancelled");
  const canCopy = turn.role === "assistant" && turn.content.length > 0;
  const showConfidence =
    turn.role === "assistant" && !isWaitingForFirstToken && turn.status !== "error" && turn.confidence !== undefined;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(turn.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error("Couldn't copy to clipboard");
    }
  };

  return (
    <div className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-secondary text-secondary-foreground" : "bg-primary/10 text-primary"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className={cn("flex max-w-[85%] flex-col gap-1.5 sm:max-w-[75%]", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm",
            isUser ? "bg-primary text-primary-foreground" : "border bg-card"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{turn.content}</p>
          ) : isWaitingForFirstToken ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <TypingIndicator />
              Thinking…
            </div>
          ) : (
            <>
              <MarkdownContent content={turn.content} />
              {isActive ? (
                <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse bg-current align-middle" />
              ) : null}
            </>
          )}

          {turn.role === "assistant" && turn.status === "error" ? (
            <p className="mt-2 flex items-center gap-1.5 text-sm text-destructive">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {turn.errorMessage ?? "Something went wrong."}
            </p>
          ) : null}
          {turn.status === "cancelled" ? (
            <p className="mt-2 text-xs text-muted-foreground">Generation cancelled.</p>
          ) : null}
        </div>

        {turn.role === "assistant" && turn.sources && turn.sources.length > 0 ? (
          <SourceCitations sources={turn.sources} results={turn.results} onSelectFile={onSelectFile} />
        ) : null}

        {showConfidence || canRetry || canCopy ? (
          <div className="flex items-center gap-3 px-1 text-xs text-muted-foreground">
            {showConfidence ? <span>Confidence: {Math.round((turn.confidence ?? 0) * 100)}%</span> : null}
            {canRetry ? (
              <button
                type="button"
                onClick={() => onRetry(turn.id)}
                className="flex items-center gap-1 hover:text-foreground"
              >
                <RotateCcw className="h-3 w-3" />
                Retry
              </button>
            ) : null}
            {canCopy ? (
              <button
                type="button"
                onClick={() => void handleCopy()}
                className="flex items-center gap-1 hover:text-foreground"
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                {copied ? "Copied" : "Copy"}
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
