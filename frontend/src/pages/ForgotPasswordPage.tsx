import { Link } from "react-router-dom";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";

export function ForgotPasswordPage() {
  return (
    <AuthLayout
      title="Forgot password"
      description="Enter your email and we'll send you a link to reset your password."
      footer={
        <>
          Remembered your password?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <ForgotPasswordForm />
    </AuthLayout>
  );
}
