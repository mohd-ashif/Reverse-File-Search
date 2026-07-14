import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createFolder, deleteFolder, estimateFolder, listFolders, scanFolder } from "@/api/folders";
import type { FolderCreate } from "@/types/folder";

export const foldersQueryKey = ["folders"] as const;

export function useFolders() {
  return useQuery({
    queryKey: foldersQueryKey,
    queryFn: listFolders,
  });
}

export function useCreateFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FolderCreate) => createFolder(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: foldersQueryKey });
    },
  });
}

export function useDeleteFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (folderId: number) => deleteFolder(folderId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: foldersQueryKey });
    },
  });
}

export function useEstimateFolder() {
  return useMutation({
    mutationFn: (payload: FolderCreate) => estimateFolder(payload),
  });
}

export function useScanFolder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ folderId, skipSensitive = true }: { folderId: number; skipSensitive?: boolean }) =>
      scanFolder(folderId, skipSensitive),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: foldersQueryKey });
      void queryClient.invalidateQueries({ queryKey: ["files"] });
    },
  });
}
