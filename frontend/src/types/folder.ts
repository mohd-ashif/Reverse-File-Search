export interface Folder {
  id: number;
  path: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FolderCreate {
  path: string;
}
