import { Link, Navigate } from "react-router-dom";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { RegisterForm } from "@/components/auth/RegisterForm";
import { useAuthStore } from "@/store/authStore";

export function RegisterPage() {
  const isAuthenticated = useAuthStore((s) => s.status === "authenticated");
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <AuthLayout
      title="Create an account"
      description="Sign up to start organizing and searching your files."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <RegisterForm />
    </AuthLayout>
  );
}
