import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { AppLayout } from "@/components/layout/AppLayout";
import { ChatPage } from "@/pages/ChatPage";
import { FilesPage } from "@/pages/FilesPage";
import { ForgotPasswordPage } from "@/pages/ForgotPasswordPage";
import { FoldersPage } from "@/pages/FoldersPage";
import { HomePage } from "@/pages/HomePage";
import { InvitationAcceptPage } from "@/pages/InvitationAcceptPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { OrganizationDashboardPage } from "@/pages/OrganizationDashboardPage";
import { OrganizationInvitationsPage } from "@/pages/OrganizationInvitationsPage";
import { OrganizationMembersPage } from "@/pages/OrganizationMembersPage";
import { OrganizationSettingsPage } from "@/pages/OrganizationSettingsPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ResetPasswordPage } from "@/pages/ResetPasswordPage";
import { SecurityPage } from "@/pages/SecurityPage";
import { SessionsPage } from "@/pages/SessionsPage";
import { VerifyEmailPage } from "@/pages/VerifyEmailPage";
import { AppBootGate } from "@/router/AppBootGate";

export function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppBootGate />}>
          {/* Public auth routes. */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route path="/invitations/accept" element={<InvitationAcceptPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route index element={<HomePage />} />
              <Route path="folders" element={<FoldersPage />} />
              <Route path="search" element={<ChatPage />} />
              <Route path="files" element={<FilesPage />} />
              <Route path="profile" element={<ProfilePage />} />
              <Route path="security" element={<SecurityPage />} />
              <Route path="security/sessions" element={<SessionsPage />} />
              <Route path="organization" element={<Navigate to="/organization/dashboard" replace />} />
              <Route path="organization/dashboard" element={<OrganizationDashboardPage />} />
              <Route path="organization/members" element={<OrganizationMembersPage />} />
              <Route path="organization/invitations" element={<OrganizationInvitationsPage />} />
              <Route path="organization/settings" element={<OrganizationSettingsPage />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
