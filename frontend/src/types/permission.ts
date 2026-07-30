export type Permission =
  | "folder.read"
  | "folder.create"
  | "folder.delete"
  | "folder.scan"
  | "file.read"
  | "file.download"
  | "file.summary"
  | "file.entities"
  | "search.execute"
  | "chat.execute"
  | "admin.users"
  | "admin.roles"
  | "admin.settings";

export const ALL_PERMISSIONS: Permission[] = [
  "folder.read",
  "folder.create",
  "folder.delete",
  "folder.scan",
  "file.read",
  "file.download",
  "file.summary",
  "file.entities",
  "search.execute",
  "chat.execute",
  "admin.users",
  "admin.roles",
  "admin.settings",
];
