import { authAxios } from "@/api/auth/axios";
import type {
  AuthResponse,
  ChangePasswordPayload,
  ForgotPasswordPayload,
  LoginPayload,
  MessageResponse,
  RegisterPayload,
  ResendVerificationPayload,
  ResetPasswordPayload,
  Session,
  UpdateMePayload,
  VerifyEmailPayload,
} from "@/types/auth";
import type { User } from "@/types/user";

export async function register(payload: RegisterPayload): Promise<MessageResponse> {
  const { data } = await authAxios.post<MessageResponse>("/auth/register", payload);
  return data;
}

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const { data } = await authAxios.post<AuthResponse>("/auth/login", payload);
  return data;
}

export async function logout(): Promise<MessageResponse> {
  const { data } = await authAxios.post<MessageResponse>("/auth/logout");
  return data;
}

export async function refresh(): Promise<AuthResponse> {
  const { data } = await authAxios.post<AuthResponse>("/auth/refresh", undefined, {
    headers: { "X-Requested-With": "XMLHttpRequest" },
  });
  return data;
}

export async function verifyEmail(payload: VerifyEmailPayload): Promise<MessageResponse> {
  const { data } = await authAxios.post<MessageResponse>("/auth/verify-email", payload);
  return data;
}

export async function resendVerification(payload: ResendVerificationPayload): Promise<MessageResponse> {
  const { data } = await authAxios.post<MessageResponse>("/auth/resend-verification", payload);
  return data;
}

export async function forgotPassword(payload: ForgotPasswordPayload): Promise<MessageResponse> {
  const { data } = await authAxios.post<MessageResponse>("/auth/forgot-password", payload);
  return data;
}

export async function resetPassword(payload: ResetPasswordPayload): Promise<MessageResponse> {
  const { data } = await authAxios.post<MessageResponse>("/auth/reset-password", payload);
  return data;
}

export async function changePassword(payload: ChangePasswordPayload): Promise<MessageResponse> {
  const { data } = await authAxios.post<MessageResponse>("/auth/change-password", payload);
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await authAxios.get<User>("/me/");
  return data;
}

export async function updateMe(payload: UpdateMePayload): Promise<User> {
  const { data } = await authAxios.patch<User>("/me/", payload);
  return data;
}

export async function getSessions(): Promise<Session[]> {
  const { data } = await authAxios.get<Session[]>("/me/sessions");
  return data;
}

export async function revokeSession(id: number): Promise<void> {
  await authAxios.delete(`/me/sessions/${id}`);
}
