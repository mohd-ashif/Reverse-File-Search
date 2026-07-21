export type ActionItemPriority = "High" | "Medium" | "Low";

export interface ActionItem {
  person: string | null;
  task: string;
  deadline: string | null;
  priority: ActionItemPriority;
}

export interface ActionItemsResult {
  file_id: number;
  filename: string;
  action_items: ActionItem[];
}
