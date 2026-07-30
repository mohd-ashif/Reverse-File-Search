import { create } from "zustand";

import type { Permission } from "@/types/permission";

interface PermissionState {
  permissions: Permission[];
  setPermissions: (permissions: Permission[]) => void;
  clear: () => void;
}

export const usePermissionStore = create<PermissionState>((set) => ({
  permissions: [],
  setPermissions: (permissions) => set({ permissions }),
  clear: () => set({ permissions: [] }),
}));
