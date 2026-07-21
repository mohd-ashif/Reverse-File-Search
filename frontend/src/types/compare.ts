export interface FileCompareResult {
  file_a: string;
  file_b: string;
  summary: string;
  differences: string[];
  added_clauses: string[];
  removed_clauses: string[];
  financial_changes: string[];
}
