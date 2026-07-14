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
