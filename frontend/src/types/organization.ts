export interface Organization {
  id: number;
  name: string;
  slug: string;
  is_active?: boolean;
  logo_url?: string | null;
  website?: string | null;
  email?: string | null;
  phone?: string | null;
  country?: string | null;
  timezone?: string;
  industry?: string | null;
  subscription_plan?: string;
  storage_limit_bytes?: number;
  storage_used_bytes?: number;
  is_platform_owner_org?: boolean;
  created_at?: string;
  updated_at?: string;
}

export type MemberStatus = "invited" | "joined" | "suspended" | "owner";

export interface OrganizationMember {
  id: number;
  user: {
    id: number;
    email: string;
    full_name: string | null;
    avatar_url: string | null;
  };
  role: string | null;
  status: MemberStatus;
  is_primary: boolean;
  created_at: string;
}

export type InvitationStatus = "pending" | "accepted" | "expired" | "revoked";

export interface Invitation {
  id: number;
  email: string;
  role: string;
  status: InvitationStatus;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
}

export interface OrganizationUpdatePayload {
  name?: string;
  logo_url?: string | null;
  website?: string | null;
  email?: string | null;
  phone?: string | null;
  country?: string | null;
  timezone?: string;
  industry?: string | null;
  storage_limit_bytes?: number;
}

export interface InviteMemberPayload {
  email: string;
  role: string;
}

export interface OrgSwitchResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  permissions: string[];
  roles: string[];
  organization: Organization | null;
}
