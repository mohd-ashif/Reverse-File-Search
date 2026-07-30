import { apiClient } from "@/api/client";
import { authAxios } from "@/api/auth/axios";
import type { AuthResponse } from "@/types/auth";
import type {
  Invitation,
  InviteMemberPayload,
  Organization,
  OrganizationMember,
  OrganizationUpdatePayload,
  OrgSwitchResponse,
} from "@/types/organization";

export async function listOrganizations(): Promise<Organization[]> {
  const { data } = await authAxios.get<Organization[]>("/organizations/");
  return data;
}

export async function getOrganization(id: number): Promise<Organization> {
  const { data } = await authAxios.get<Organization>(`/organizations/${id}`);
  return data;
}

export async function updateOrganization(id: number, payload: OrganizationUpdatePayload): Promise<Organization> {
  const { data } = await authAxios.patch<Organization>(`/organizations/${id}`, payload);
  return data;
}

export async function listMembers(organizationId: number): Promise<OrganizationMember[]> {
  const { data } = await authAxios.get<OrganizationMember[]>(`/organizations/${organizationId}/members`);
  return data;
}

export async function inviteMember(organizationId: number, payload: InviteMemberPayload): Promise<Invitation> {
  const { data } = await authAxios.post<Invitation>(`/organizations/${organizationId}/invite`, payload);
  return data;
}

export async function listInvitations(organizationId: number): Promise<Invitation[]> {
  const { data } = await authAxios.get<Invitation[]>(`/organizations/${organizationId}/invitations`);
  return data;
}

export async function resendInvitation(organizationId: number, invitationId: number): Promise<Invitation> {
  const { data } = await authAxios.post<Invitation>(
    `/organizations/${organizationId}/invitations/${invitationId}/resend`
  );
  return data;
}

export async function revokeInvitation(organizationId: number, invitationId: number): Promise<void> {
  await authAxios.delete(`/organizations/${organizationId}/invitations/${invitationId}`);
}

export async function changeMemberRole(memberId: number, role: string): Promise<OrganizationMember> {
  const { data } = await authAxios.patch<OrganizationMember>(`/members/${memberId}/role`, { role });
  return data;
}

export async function removeMember(memberId: number): Promise<void> {
  await authAxios.delete(`/members/${memberId}`);
}

export async function suspendMember(memberId: number): Promise<OrganizationMember> {
  const { data } = await authAxios.post<OrganizationMember>(`/members/${memberId}/suspend`);
  return data;
}

export async function switchOrganization(organizationId: number): Promise<OrgSwitchResponse> {
  const { data } = await authAxios.post<OrgSwitchResponse>(`/organizations/${organizationId}/switch`);
  return data;
}

export interface AcceptInvitationPayload {
  token: string;
  password: string;
  full_name?: string;
}

export async function acceptInvitation(payload: AcceptInvitationPayload): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>("/invitations/accept", payload);
  return data;
}
