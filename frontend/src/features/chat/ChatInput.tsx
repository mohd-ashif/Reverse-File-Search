import { useEffect, useRef, useState } from "react";
import { Square, ArrowUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SearchSuggestionsDropdown } from "@/features/chat/SearchSuggestionsDropdown";
import { useSearchSuggestions } from "@/hooks/useSearchSuggestions";

const MAX_TEXTAREA_HEIGHT_PX = 200;

interface ChatInputProps {
  isStreaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

export function ChatInput({ isStreaming, onSend, onStop }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const { data: suggestions, isLoading: suggestionsLoading } = useSearchSuggestions(value, showSuggestions);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }, [value]);

  const handleSend = (text: string = value) => {
    if (!text.trim() || isStreaming) return;
    onSend(text);
    setValue("");
    setShowSuggestions(false);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    } else if (event.key === "Escape") {
      setShowSuggestions(false);
    }
  };

  return (
    <div className="relative flex items-end gap-2 rounded-xl border bg-card p-2 shadow-sm">
      {showSuggestions ? (
        <SearchSuggestionsDropdown
          suggestions={suggestions}
          isLoading={suggestionsLoading}
          onSelect={handleSend}
        />
      ) : null}
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onFocus={() => setShowSuggestions(true)}
        onBlur={() => setShowSuggestions(false)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your indexed files..."
        rows={1}
        className="max-h-[200px] flex-1 resize-none overflow-y-auto border-0 bg-transparent shadow-none focus-visible:ring-0"
        aria-label="Chat message"
      />
      {isStreaming ? (
        <Button type="button" size="icon" variant="outline" onClick={onStop} aria-label="Stop generating">
          <Square className="h-4 w-4" />
        </Button>
      ) : (
        <Button
          type="button"
          size="icon"
          onClick={() => handleSend()}
          disabled={!value.trim()}
          aria-label="Send message"
        >
          <ArrowUp className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
