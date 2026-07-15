export interface FileSummary {
  id: number;
  file_id: number;
  executive_summary: string;
  key_points: string[];
  important_dates: string[];
  people: string[];
  organizations: string[];
  risks: string[];
  action_items: string[];
  model: string;
  created_at: string;
  updated_at: string;
}
