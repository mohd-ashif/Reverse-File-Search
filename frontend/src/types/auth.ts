import type { Organization } from "@/types/organization";
import type { Permission } from "@/types/permission";
import type { User } from "@/types/user";

export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
  user: User;
  permissions: Permission[];
  roles: string[];
  organization: Organization | null;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface ForgotPasswordPayload {
  email: string;
}

export interface ResetPasswordPayload {
  token: string;
  new_password: string;
}

export interface ChangePasswordPayload {
  current_password: string;
  new_password: string;
}

export interface VerifyEmailPayload {
  token: string;
}

export interface ResendVerificationPayload {
  email: string;
}

export interface UpdateMePayload {
  full_name?: string;
  first_name?: string;
  last_name?: string;
  phone?: string;
  avatar_url?: string;
}

export interface Session {
  id: number;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string;
  is_current: boolean;
}

export interface MessageResponse {
  message: string;
}
