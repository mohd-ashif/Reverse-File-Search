import { Link } from "react-router-dom";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";

export function ResetPasswordPage() {
  return (
    <AuthLayout
      title="Reset password"
      description="Choose a new password for your account."
      footer={
        <>
          Remembered your password?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <ResetPasswordForm />
    </AuthLayout>
  );
}
