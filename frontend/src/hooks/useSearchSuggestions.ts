import { useQuery } from "@tanstack/react-query";

import { getSearchSuggestions } from "@/api/search";
import { useDebounce } from "@/hooks/useDebounce";

/** Powers the search box's autocomplete dropdown. Debounces the query text so
 * it re-fetches (recent/popular/AI-generated) as the user types, without
 * firing a request on every keystroke. Only active while `enabled` (the box
 * is focused). */
export function useSearchSuggestions(query: string, enabled: boolean) {
  const debouncedQuery = useDebounce(query, 250);

  return useQuery({
    queryKey: ["search-suggestions", debouncedQuery],
    queryFn: () => getSearchSuggestions(debouncedQuery),
    enabled,
    placeholderData: (prev) => prev,
  });
}
