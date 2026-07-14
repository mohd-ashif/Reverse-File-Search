import { useQuery } from "@tanstack/react-query";

import { getFile, listFiles } from "@/api/files";

export function useFiles(folderId?: number) {
  return useQuery({
    queryKey: ["files", folderId ?? "all"],
    queryFn: () => listFiles(folderId),
  });
}

export function useFile(fileId: number | null) {
  return useQuery({
    queryKey: ["files", "detail", fileId],
    queryFn: () => getFile(fileId as number),
    enabled: fileId !== null,
  });
}
