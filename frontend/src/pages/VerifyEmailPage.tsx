import { AuthLayout } from "@/components/auth/AuthLayout";
import { VerifyEmail } from "@/components/auth/VerifyEmail";

export function VerifyEmailPage() {
  return (
    <AuthLayout title="Verify your email" description="Confirming your account.">
      <VerifyEmail />
    </AuthLayout>
  );
}
