import { apiClient } from "@/api/client";
import type { Folder, FolderCreate } from "@/types/folder";
import type { FolderEstimate, FolderScanResponse, StartScanResponse } from "@/types/scan";

export async function listFolders(): Promise<Folder[]> {
  const { data } = await apiClient.get<Folder[]>("/folders/");
  return data;
}

export async function createFolder(payload: FolderCreate): Promise<Folder> {
  const { data } = await apiClient.post<Folder>("/folders/", payload);
  return data;
}

export async function deleteFolder(folderId: number): Promise<void> {
  await apiClient.delete(`/folders/${folderId}`);
}

export async function scanFolder(folderId: number, skipSensitive = true): Promise<FolderScanResponse> {
  const { data } = await apiClient.post<FolderScanResponse>(
    `/folders/${folderId}/scan`,
    null,
    { params: { skip_sensitive: skipSensitive } }
  );
  return data;
}

export async function estimateFolder(payload: FolderCreate): Promise<FolderEstimate> {
  const { data } = await apiClient.post<FolderEstimate>("/folders/estimate", payload);
  return data;
}

export async function startFolderScan(folderId: number, skipSensitive = true): Promise<StartScanResponse> {
  const { data } = await apiClient.post<StartScanResponse>(
    `/folders/${folderId}/scan/start`,
    null,
    { params: { skip_sensitive: skipSensitive } }
  );
  return data;
}
