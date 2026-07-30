import { Link } from "react-router-dom";

import { AuthLayout } from "@/components/auth/AuthLayout";
import { InvitationAcceptForm } from "@/components/auth/InvitationAcceptForm";

export function InvitationAcceptPage() {
  return (
    <AuthLayout
      title="Accept your invitation"
      description="Set a password to finish joining your organization."
      footer={
        <>
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <InvitationAcceptForm />
    </AuthLayout>
  );
}
