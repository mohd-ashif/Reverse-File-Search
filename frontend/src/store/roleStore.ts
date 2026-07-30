import { create } from "zustand";

interface RoleState {
  roles: string[];
  setRoles: (roles: string[]) => void;
  clear: () => void;
}

export const useRoleStore = create<RoleState>((set) => ({
  roles: [],
  setRoles: (roles) => set({ roles }),
  clear: () => set({ roles: [] }),
}));
