export interface ScanResult {
  folder_id: number;
  added: number;
  modified: number;
  deleted: number;
  skipped: number;
  skipped_sensitive: number;
}

export interface IndexResult {
  extracted: number;
  embedded: number;
  failed: number;
}

export interface FolderScanResponse {
  scan: ScanResult;
  index: IndexResult;
}

export interface FolderEstimate {
  path: string;
  estimated_files: number;
  estimated_supported_files: number;
  unsupported_files: number;
  approx_scan_seconds: number;
  estimated_storage_bytes: number;
  large_files_detected: number;
  large_file_threshold_bytes: number;
  sensitive_files_detected: number;
  sensitive_file_samples: string[];
}

export interface StartScanResponse {
  scan_id: string;
}

export const SCAN_STAGES = [
  "finding_files",
  "reading_metadata",
  "extracting_text",
  "generating_embeddings",
  "saving_to_database",
  "finalizing",
] as const;

export type ScanStage = (typeof SCAN_STAGES)[number];

export const SCAN_STAGE_LABEL: Record<ScanStage, string> = {
  finding_files: "Finding files",
  reading_metadata: "Reading metadata",
  extracting_text: "Extracting text",
  generating_embeddings: "Generating embeddings",
  saving_to_database: "Saving to database",
  finalizing: "Finalizing",
};

export interface FailedScanFile {
  filename: string;
  path: string;
  error: string;
}

export interface ScanProgressEvent {
  type: "progress";
  scan_id: string;
  stage: ScanStage;
  current_file: string | null;
  files_processed: number;
  files_total: number;
  files_remaining: number;
  estimated_remaining_seconds: number | null;
  elapsed_seconds: number;
}

export interface ScanSummaryEvent {
  type: "summary";
  scan_id: string;
  scan: ScanResult;
  index: IndexResult;
  succeeded_files: string[];
  failed_files: FailedScanFile[];
  elapsed_seconds: number;
}

export interface ScanErrorEvent {
  type: "error";
  scan_id: string;
  message: string;
  elapsed_seconds: number;
}

export type ScanSocketEvent = ScanProgressEvent | ScanSummaryEvent | ScanErrorEvent;
