import { Clock, Sparkles, TrendingUp } from "lucide-react";

import type { SearchSuggestions } from "@/types/searchSuggestions";

interface SearchSuggestionsDropdownProps {
  suggestions: SearchSuggestions | undefined;
  isLoading: boolean;
  onSelect: (query: string) => void;
}

interface Section {
  key: keyof SearchSuggestions;
  label: string;
  icon: typeof Clock;
}

const SECTIONS: Section[] = [
  { key: "recent", label: "Recent searches", icon: Clock },
  { key: "popular", label: "Popular searches", icon: TrendingUp },
  { key: "ai_generated", label: "AI-generated searches", icon: Sparkles },
];

export function SearchSuggestionsDropdown({ suggestions, isLoading, onSelect }: SearchSuggestionsDropdownProps) {
  const sections = SECTIONS.map((section) => ({
    ...section,
    items: suggestions?.[section.key] ?? [],
  })).filter((section) => section.items.length > 0);

  if (!isLoading && sections.length === 0) {
    return null;
  }

  return (
    <div
      className="absolute bottom-full left-0 z-20 mb-2 max-h-80 w-full overflow-y-auto rounded-xl border bg-popover p-2 text-popover-foreground shadow-md"
      // Selecting a suggestion shouldn't first blur the textarea (which would
      // close this dropdown before the click registers).
      onMouseDown={(event) => event.preventDefault()}
    >
      {isLoading && sections.length === 0 ? (
        <p className="px-2 py-1.5 text-xs text-muted-foreground">Loading suggestions…</p>
      ) : (
        sections.map((section) => (
          <div key={section.key} className="mb-1 last:mb-0">
            <div className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-muted-foreground">
              <section.icon className="h-3.5 w-3.5" />
              {section.label}
            </div>
            {section.items.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onSelect(item)}
                className="block w-full truncate rounded-lg px-2.5 py-1.5 text-left text-sm hover:bg-accent"
                title={item}
              >
                {item}
              </button>
            ))}
          </div>
        ))
      )}
    </div>
  );
}
