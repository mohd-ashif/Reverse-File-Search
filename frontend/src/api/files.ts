import { API_BASE_URL, apiClient, ApiError } from "@/api/client";
import type { ActionItemsResult } from "@/types/actionItems";
import type { FileCompareResult } from "@/types/compare";
import type { ContractRiskAnalysis } from "@/types/contractRisk";
import type { ExtractedText } from "@/types/extractedText";
import type { IndexedFile } from "@/types/file";
import type { FileSummary } from "@/types/summary";
import type { FileTags } from "@/types/tag";

export async function listFiles(folderId?: number, tag?: string): Promise<IndexedFile[]> {
  const { data } = await apiClient.get<IndexedFile[]>("/files/", {
    params: { folder_id: folderId, tag },
  });
  return data;
}

export async function listFileTags(folderId?: number): Promise<FileTags[]> {
  const { data } = await apiClient.get<FileTags[]>("/files/tags", {
    params: folderId ? { folder_id: folderId } : undefined,
  });
  return data;
}

export async function getFileTags(fileId: number): Promise<FileTags> {
  const { data } = await apiClient.get<FileTags>(`/files/${fileId}/tags`);
  return data;
}

export async function getFile(fileId: number): Promise<IndexedFile> {
  const { data } = await apiClient.get<IndexedFile>(`/files/${fileId}`);
  return data;
}

export function getFileContentUrl(fileId: number): string {
  return `${API_BASE_URL}/files/${fileId}/content`;
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

export async function compareFiles(fileIdA: number, fileIdB: number): Promise<FileCompareResult> {
  const { data } = await apiClient.post<FileCompareResult>("/files/compare", {
    file_id_a: fileIdA,
    file_id_b: fileIdB,
  });
  return data;
}

export async function analyzeContractRisks(fileId: number): Promise<ContractRiskAnalysis> {
  const { data } = await apiClient.post<ContractRiskAnalysis>(`/files/${fileId}/contract-risks`);
  return data;
}

export async function extractActionItems(fileId: number): Promise<ActionItemsResult> {
  const { data } = await apiClient.post<ActionItemsResult>(`/files/${fileId}/action-items`);
  return data;
}

export async function getExtractedText(fileId: number): Promise<ExtractedText> {
  const { data } = await apiClient.get<ExtractedText>(`/files/${fileId}/extracted-text`);
  return data;
}
