import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { MailCheck } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useForgotPassword } from "@/hooks/useAuth";

const forgotPasswordSchema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email address"),
});

type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export function ForgotPasswordForm() {
  const [submitted, setSubmitted] = useState(false);
  const forgotPassword = useForgotPassword();

  const form = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = (values: ForgotPasswordFormValues) => {
    forgotPassword.mutate(values, {
      // Always show the generic success state on a successful response,
      // regardless of whether the email actually exists — this avoids
      // leaking account existence to an attacker (enumeration avoidance).
      onSuccess: () => setSubmitted(true),
      onError: (error) => {
        // Only genuine network/5xx failures get a toast; a "success"
        // response that merely doesn't confirm the email exists is handled
        // above as a success.
        toast.error("Something went wrong", {
          description: error instanceof ApiError ? error.message : "Please try again.",
        });
      },
    });
  };

  if (submitted) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <MailCheck className="h-10 w-10 text-primary" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Check your email</h3>
        <p className="max-w-sm text-sm text-muted-foreground">
          If an account exists for that email address, we've sent a link to reset your password.
        </p>
        <Button asChild variant="outline" className="mt-2">
          <Link to="/login">Back to sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" placeholder="you@example.com" autoComplete="email" autoFocus {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full" disabled={forgotPassword.isPending}>
          {forgotPassword.isPending ? <Spinner className="mr-2" /> : null}
          Send reset link
        </Button>
      </form>
    </Form>
  );
}
