import { apiClient, ApiError } from "@/api/client";
import type { IndexedFile } from "@/types/file";
import type { FileSummary } from "@/types/summary";

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

export async function getFileSummary(fileId: number): Promise<FileSummary | null> {
  try {
    const { data } = await apiClient.get<FileSummary>(`/files/${fileId}/summary`);
    return data;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function generateFileSummary(fileId: number): Promise<FileSummary> {
  const { data } = await apiClient.post<FileSummary>(`/files/${fileId}/summary`);
  return data;
}
