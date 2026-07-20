import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { generateFileSummary, getFile, getFileSummary, getFileTags, listFileTags, listFiles } from "@/api/files";

export function useFiles(folderId?: number, tag?: string) {
  return useQuery({
    queryKey: ["files", folderId ?? "all", tag ?? "all"],
    queryFn: () => listFiles(folderId, tag),
  });
}

export function useFileTags(fileId: number | null) {
  return useQuery({
    queryKey: ["files", "tags", fileId],
    queryFn: () => getFileTags(fileId as number),
    enabled: fileId !== null,
  });
}

export function useAllFileTags(folderId?: number) {
  return useQuery({
    queryKey: ["files", "tags", "all", folderId ?? "all"],
    queryFn: () => listFileTags(folderId),
  });
}

export function useFile(fileId: number | null) {
  return useQuery({
    queryKey: ["files", "detail", fileId],
    queryFn: () => getFile(fileId as number),
    enabled: fileId !== null,
  });
}

export function useFileSummary(fileId: number | null) {
  return useQuery({
    queryKey: ["files", "summary", fileId],
    queryFn: () => getFileSummary(fileId as number),
    enabled: fileId !== null,
  });
}

export function useGenerateFileSummary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fileId: number) => generateFileSummary(fileId),
    onSuccess: (summary, fileId) => {
      queryClient.setQueryData(["files", "summary", fileId], summary);
    },
  });
}
