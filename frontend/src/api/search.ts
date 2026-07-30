import { authAxios as apiClient } from "@/api/auth/axios";
import type { SearchSuggestions } from "@/types/searchSuggestions";

export async function getSearchSuggestions(q: string): Promise<SearchSuggestions> {
  const { data } = await apiClient.get<SearchSuggestions>("/search/suggestions", {
    params: { q },
  });
  return data;
}
