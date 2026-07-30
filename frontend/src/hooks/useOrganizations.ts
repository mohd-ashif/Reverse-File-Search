import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as orgApi from "@/api/organizations";
import { useAuthStore } from "@/store/authStore";
import { useOrganizationStore } from "@/store/organizationStore";
import { usePermissionStore } from "@/store/permissionStore";
import { useRoleStore } from "@/store/roleStore";
import type { InviteMemberPayload, OrganizationUpdatePayload } from "@/types/organization";
import type { Permission } from "@/types/permission";

export const organizationsQueryKey = ["organizations"] as const;
export const membersQueryKey = (orgId: number) => ["organizations", orgId, "members"] as const;
export const invitationsQueryKey = (orgId: number) => ["organizations", orgId, "invitations"] as const;

export function useOrganizations() {
  const status = useAuthStore((s) => s.status);
  return useQuery({
    queryKey: organizationsQueryKey,
    queryFn: orgApi.listOrganizations,
    enabled: status === "authenticated",
  });
}

export function useMembers(organizationId: number | undefined) {
  return useQuery({
    queryKey: membersQueryKey(organizationId ?? -1),
    queryFn: () => orgApi.listMembers(organizationId as number),
    enabled: organizationId != null,
  });
}

export function useInvitations(organizationId: number | undefined) {
  return useQuery({
    queryKey: invitationsQueryKey(organizationId ?? -1),
    queryFn: () => orgApi.listInvitations(organizationId as number),
    enabled: organizationId != null,
  });
}

export function useUpdateOrganization(organizationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrganizationUpdatePayload) => orgApi.updateOrganization(organizationId, payload),
    onSuccess: (org) => {
      useOrganizationStore.getState().setOrganization(org);
      void queryClient.invalidateQueries({ queryKey: organizationsQueryKey });
    },
  });
}

export function useInviteMember(organizationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: InviteMemberPayload) => orgApi.inviteMember(organizationId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invitationsQueryKey(organizationId) });
    },
  });
}

export function useResendInvitation(organizationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: number) => orgApi.resendInvitation(organizationId, invitationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invitationsQueryKey(organizationId) });
    },
  });
}

export function useRevokeInvitation(organizationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: number) => orgApi.revokeInvitation(organizationId, invitationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: invitationsQueryKey(organizationId) });
    },
  });
}

export function useChangeMemberRole(organizationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ memberId, role }: { memberId: number; role: string }) => orgApi.changeMemberRole(memberId, role),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: membersQueryKey(organizationId) });
    },
  });
}

export function useRemoveMember(organizationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memberId: number) => orgApi.removeMember(memberId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: membersQueryKey(organizationId) });
    },
  });
}

export function useSuspendMember(organizationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memberId: number) => orgApi.suspendMember(memberId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: membersQueryKey(organizationId) });
    },
  });
}

export function useSwitchOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (organizationId: number) => orgApi.switchOrganization(organizationId),
    onSuccess: (data) => {
      const currentUser = useAuthStore.getState().user;
      if (currentUser) useAuthStore.getState().setSession(currentUser, data.accessToken);
      usePermissionStore.getState().setPermissions(data.permissions as Permission[]);
      useRoleStore.getState().setRoles(data.roles);
      useOrganizationStore.getState().setOrganization(data.organization);
      queryClient.clear();
    },
  });
}

export function useAcceptInvitation() {
  return useMutation({ mutationFn: orgApi.acceptInvitation });
}
