import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useResendVerification, useVerifyEmail } from "@/hooks/useAuth";

const resendSchema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
});

type ResendFormValues = z.infer<typeof resendSchema>;

type VerifyState = "loading" | "success" | "error" | "missing-token";

function ResendVerificationForm() {
  const resendVerification = useResendVerification();
  const [sent, setSent] = useState(false);

  const form = useForm<ResendFormValues>({
    resolver: zodResolver(resendSchema),
    defaultValues: { email: "" },
  });

  if (sent) {
    return (
      <p className="text-sm text-muted-foreground">
        If that email is registered, a new verification link is on its way.
      </p>
    );
  }

  const onSubmit = (values: ResendFormValues) => {
    resendVerification.mutate(values, {
      onSuccess: () => setSent(true),
      onError: (error) => {
        toast.error("Failed to resend verification email", {
          description: error instanceof Error ? error.message : "Please try again.",
        });
      },
    });
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="w-full space-y-3">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="you@example.com" autoComplete="email" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit" variant="outline" className="w-full" disabled={resendVerification.isPending}>
          {resendVerification.isPending ? <Spinner className="mr-2" /> : null}
          Resend verification link
        </Button>
      </form>
    </Form>
  );
}

/**
 * Fires `/auth/verify-email` exactly once on mount using the `token` query
 * param. The backend returns a generic `InvalidTokenError` for both
 * "not found" and "expired" tokens, so we can't distinguish the two cases
 * from the response — a single generic failure state covers both, with an
 * inline resend-verification form as the recovery path (there's no
 * dedicated resend page in this phase's scope).
 */
export function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const verifyEmail = useVerifyEmail();
  const firedRef = useRef(false);
  const [state, setState] = useState<VerifyState>(token ? "loading" : "missing-token");

  useEffect(() => {
    if (!token || firedRef.current) return;
    firedRef.current = true;

    verifyEmail.mutate(
      { token },
      {
        onSuccess: () => setState("success"),
        onError: () => setState("error"),
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (state === "missing-token") {
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <XCircle className="h-10 w-10 text-destructive" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Invalid verification link</h3>
        <p className="max-w-sm text-sm text-muted-foreground">
          This link is missing its verification token.
        </p>
        <ResendVerificationForm />
      </div>
    );
  }

  if (state === "loading") {
    return (
      <div className="flex flex-col items-center gap-3 py-8 text-center">
        <Spinner className="h-8 w-8" />
        <p className="text-sm text-muted-foreground">Verifying your email…</p>
      </div>
    );
  }

  if (state === "success") {
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <CheckCircle2 className="h-10 w-10 text-green-500" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Email verified</h3>
        <p className="max-w-sm text-sm text-muted-foreground">Your account is now verified. You can sign in.</p>
        <Button asChild className="mt-2">
          <Link to="/login">Go to login</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-3 py-4 text-center">
      <XCircle className="h-10 w-10 text-destructive" aria-hidden="true" />
      <h3 className="text-lg font-semibold">This link is invalid or has expired</h3>
      <p className="max-w-sm text-sm text-muted-foreground">
        Enter your email below to get a new verification link.
      </p>
      <ResendVerificationForm />
    </div>
  );
}
