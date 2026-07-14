export type FileType = "pdf" | "docx" | "txt" | "markdown" | "image" | "excel" | "unknown";

export type FileIndexStatus = "pending" | "extracted" | "embedded" | "failed";

export interface IndexedFile {
  id: number;
  folder_id: number;
  absolute_path: string;
  filename: string;
  extension: string;
  file_type: FileType;
  size_bytes: number;
  checksum: string;
  status: FileIndexStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}
