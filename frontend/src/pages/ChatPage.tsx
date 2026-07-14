import { useEffect, useRef, useState } from "react";

import { ChatInput } from "@/features/chat/ChatInput";
import { ChatMessageBubble } from "@/features/chat/ChatMessageBubble";
import { SuggestedQuestions } from "@/features/chat/SuggestedQuestions";
import { FileDetailDialog } from "@/features/files/FileDetailDialog";
import { useChat } from "@/hooks/useChat";
import { useFile } from "@/hooks/useFiles";

const SCROLL_BOTTOM_THRESHOLD_PX = 80;

export function ChatPage() {
  const { turns, sendMessage, retryTurn, cancel, isStreaming } = useChat();
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null);
  const { data: selectedFile } = useFile(selectedFileId);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const autoScrollRef = useRef(true);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    autoScrollRef.current = distanceFromBottom < SCROLL_BOTTOM_THRESHOLD_PX;
  };

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !autoScrollRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [turns]);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-muted-foreground">
          Ask questions about the content of your indexed files, in plain language.
        </p>
      </div>

      {turns.length === 0 ? (
        <SuggestedQuestions onSelect={sendMessage} />
      ) : (
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="mt-4 flex-1 space-y-6 overflow-y-auto px-1 pb-4"
        >
          {turns.map((turn) => (
            <ChatMessageBubble key={turn.id} turn={turn} onRetry={retryTurn} onSelectFile={setSelectedFileId} />
          ))}
        </div>
      )}

      <div className="sticky bottom-0 mt-2 bg-background pt-2">
        <ChatInput isStreaming={isStreaming} onSend={sendMessage} onStop={cancel} />
        <p className="mt-2 text-center text-xs text-muted-foreground">
          AI answers are generated from your indexed files and may be incomplete.
        </p>
      </div>

      <FileDetailDialog file={selectedFile ?? null} onOpenChange={(open) => !open && setSelectedFileId(null)} />
    </div>
  );
}
