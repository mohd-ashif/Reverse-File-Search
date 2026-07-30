import { create } from "zustand";

import type { Organization } from "@/types/organization";

interface OrganizationState {
  organization: Organization | null;
  memberships: Organization[];
  setOrganization: (organization: Organization | null) => void;
  setMemberships: (memberships: Organization[]) => void;
  clear: () => void;
}

export const useOrganizationStore = create<OrganizationState>((set) => ({
  organization: null,
  memberships: [],
  setOrganization: (organization) => set({ organization }),
  setMemberships: (memberships) => set({ memberships }),
  clear: () => set({ organization: null, memberships: [] }),
}));
