import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FolderOpen, X } from "lucide-react";

import { ChatInput } from "@/features/chat/ChatInput";
import { ChatMessageBubble } from "@/features/chat/ChatMessageBubble";
import { SuggestedQuestions } from "@/features/chat/SuggestedQuestions";
import { FileDetailDialog } from "@/features/files/FileDetailDialog";
import { useChat } from "@/hooks/useChat";
import { useFile } from "@/hooks/useFiles";
import { useFolders } from "@/hooks/useFolders";

const SCROLL_BOTTOM_THRESHOLD_PX = 80;

const FOLDER_SUGGESTIONS = [
  "What invoices are unpaid?",
  "What's the largest purchase?",
  "Who spent the most?",
  "Summarize the contracts in this folder.",
];

function FolderScopeBanner({ folderPath }: { folderPath: string }) {
  return (
    <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border bg-muted/50 px-3 py-2 text-sm">
      <div className="flex min-w-0 items-center gap-2">
        <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className="text-muted-foreground">Chatting within folder:</span>
        <span className="truncate font-mono text-xs" title={folderPath}>
          {folderPath}
        </span>
      </div>
      <Link
        to="/search"
        className="flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
      >
        <X className="h-3.5 w-3.5" />
        Exit folder chat
      </Link>
    </div>
  );
}

/** The conversation itself, keyed by scope at the call site so switching
 * folders (or leaving folder scope) starts a fresh conversation instead of
 * carrying over turns from a different scope. */
function ChatConversation({ folderId }: { folderId?: number }) {
  const { turns, sendMessage, retryTurn, cancel, isStreaming } = useChat({ folderId });
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
    <>
      {turns.length === 0 ? (
        <SuggestedQuestions
          onSelect={sendMessage}
          suggestions={folderId !== undefined ? FOLDER_SUGGESTIONS : undefined}
          title={folderId !== undefined ? "Ask about this folder" : undefined}
          description={
            folderId !== undefined
              ? "Answers are grounded only in documents inside this folder, with citations back to the source file."
              : undefined
          }
        />
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
    </>
  );
}

export function ChatPage() {
  const [searchParams] = useSearchParams();
  const folderIdParam = searchParams.get("folderId");
  const folderId = folderIdParam ? Number(folderIdParam) : undefined;

  const { data: folders } = useFolders();
  const folder = folderId !== undefined ? folders?.find((f) => f.id === folderId) : undefined;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="text-sm text-muted-foreground">
          Ask questions about the content of your indexed files, in plain language.
        </p>
      </div>

      {folderId !== undefined && folder ? <FolderScopeBanner folderPath={folder.path} /> : null}

      <ChatConversation key={folderId ?? "global"} folderId={folderId} />
    </div>
  );
}
