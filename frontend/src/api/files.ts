import { apiClient } from "@/api/client";
import type { IndexedFile } from "@/types/file";

export async function listFiles(folderId?: number): Promise<IndexedFile[]> {
  const { data } = await apiClient.get<IndexedFile[]>("/files/", {
    params: folderId ? { folder_id: folderId } : undefined,
  });
  return data;
}

export async function getFile(fileId: number): Promise<IndexedFile> {
  const { data } = await apiClient.get<IndexedFile>(`/files/${fileId}`);
  return data;
}
