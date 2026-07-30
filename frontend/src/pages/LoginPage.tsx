import { Link, Navigate } from "react-router-dom";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { LoginForm } from "@/components/auth/LoginForm";
import { useAuthStore } from "@/store/authStore";

export function LoginPage() {
  const isAuthenticated = useAuthStore((s) => s.status === "authenticated");
  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return (
    <AuthLayout
      title="Sign in"
      description="Welcome back — enter your details to continue."
      footer={
        <>
          Don't have an account?{" "}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Register
          </Link>
        </>
      }
    >
      <LoginForm />
    </AuthLayout>
  );
}
