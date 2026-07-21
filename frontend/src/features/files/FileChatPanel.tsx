import { useEffect, useRef } from "react";

import { ChatInput } from "@/features/chat/ChatInput";
import { ChatMessageBubble } from "@/features/chat/ChatMessageBubble";
import { SuggestedQuestions } from "@/features/chat/SuggestedQuestions";
import { useChat } from "@/hooks/useChat";

const FILE_SUGGESTIONS = ["Summarize this file.", "Explain clause 4.", "Who signed?", "When was payment made?"];

const SCROLL_BOTTOM_THRESHOLD_PX = 80;

interface FileChatPanelProps {
  fileId: number;
  filename: string;
}

/** Chat scoped to a single file — answers are grounded only in that file's
 * own content (see SearchService.retrieve_file), never other indexed files. */
export function FileChatPanel({ fileId, filename }: FileChatPanelProps) {
  const { turns, sendMessage, retryTurn, cancel, isStreaming } = useChat({ fileId });

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
    <div className="flex h-[60vh] flex-col">
      {turns.length === 0 ? (
        <SuggestedQuestions
          onSelect={sendMessage}
          suggestions={FILE_SUGGESTIONS}
          title="Ask about this file"
          description={`Answers are grounded only in "${filename}" — nothing outside it.`}
          compact
        />
      ) : (
        <div ref={scrollRef} onScroll={handleScroll} className="flex-1 space-y-6 overflow-y-auto px-1 pb-4">
          {turns.map((turn) => (
            <ChatMessageBubble key={turn.id} turn={turn} onRetry={retryTurn} onSelectFile={() => {}} />
          ))}
        </div>
      )}

      <div className="sticky bottom-0 mt-2 bg-background pt-2">
        <ChatInput isStreaming={isStreaming} onSend={sendMessage} onStop={cancel} />
      </div>
    </div>
  );
}
