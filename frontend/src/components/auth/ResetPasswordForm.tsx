import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useResetPassword } from "@/hooks/useAuth";
import { passwordSchema } from "@/lib/passwordSchema";

const resetPasswordSchema = z
  .object({
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export function ResetPasswordForm() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const resetPassword = useResetPassword();

  const form = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  if (!token) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <ShieldAlert className="h-10 w-10 text-destructive" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Invalid or missing reset link</h3>
        <p className="max-w-sm text-sm text-muted-foreground">
          This password reset link is missing its token. Request a new one below.
        </p>
        <Button asChild variant="outline" className="mt-2">
          <Link to="/forgot-password">Request a new link</Link>
        </Button>
      </div>
    );
  }

  const onSubmit = (values: ResetPasswordFormValues) => {
    resetPassword.mutate(
      { token, new_password: values.password },
      {
        onSuccess: () => {
          toast.success("Password reset successfully. Please sign in.");
          navigate("/login", { replace: true });
        },
        onError: (error) => {
          if (error instanceof ApiError && (error.status === 400 || error.status === 404)) {
            form.setError("password", { message: "This reset link is invalid or has expired." });
            return;
          }
          toast.error("Failed to reset password", {
            description: error instanceof Error ? error.message : "Unknown error",
          });
        },
      }
    );
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>New password</FormLabel>
              <div className="relative">
                <FormControl>
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    autoComplete="new-password"
                    className="pr-10"
                    autoFocus
                    {...field}
                  />
                </FormControl>
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="confirmPassword"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Confirm new password</FormLabel>
              <FormControl>
                <Input
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  autoComplete="new-password"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full" disabled={resetPassword.isPending}>
          {resetPassword.isPending ? <Spinner className="mr-2" /> : null}
          Reset password
        </Button>
      </form>
    </Form>
  );
}
