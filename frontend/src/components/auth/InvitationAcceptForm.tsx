import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { applyAuthResponse } from "@/hooks/useAuth";
import { useAcceptInvitation } from "@/hooks/useOrganizations";
import { passwordSchema } from "@/lib/passwordSchema";

const acceptSchema = z
  .object({
    full_name: z.string().trim().max(200).optional().or(z.literal("")),
    password: passwordSchema,
    confirmPassword: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type AcceptFormValues = z.infer<typeof acceptSchema>;

export function InvitationAcceptForm() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();
  const acceptInvitation = useAcceptInvitation();

  const form = useForm<AcceptFormValues>({
    resolver: zodResolver(acceptSchema),
    defaultValues: { full_name: "", password: "", confirmPassword: "" },
  });

  if (!token) {
    return (
      <div className="flex flex-col items-center gap-3 py-4 text-center">
        <ShieldAlert className="h-10 w-10 text-destructive" aria-hidden="true" />
        <h3 className="text-lg font-semibold">Invalid or missing invitation link</h3>
        <p className="max-w-sm text-sm text-muted-foreground">
          This invitation link is missing its token. Ask your organization admin to resend it.
        </p>
      </div>
    );
  }

  const onSubmit = (values: AcceptFormValues) => {
    acceptInvitation.mutate(
      { token, password: values.password, full_name: values.full_name || undefined },
      {
        onSuccess: (data) => {
          applyAuthResponse(data);
          toast.success("Welcome aboard!");
          navigate("/", { replace: true });
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === 400) {
            form.setError("password", { message: "This invitation is invalid, expired, or already used." });
            return;
          }
          toast.error("Failed to accept invitation", {
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
          name="full_name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Full name</FormLabel>
              <FormControl>
                <Input placeholder="Jane Doe" autoComplete="name" autoFocus {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <div className="relative">
                <FormControl>
                  <Input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    autoComplete="new-password"
                    className="pr-10"
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
              <FormLabel>Confirm password</FormLabel>
              <FormControl>
                <Input type={showPassword ? "text" : "password"} autoComplete="new-password" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" className="w-full" disabled={acceptInvitation.isPending}>
          {acceptInvitation.isPending ? <Spinner className="mr-2" /> : null}
          Accept invitation
        </Button>
      </form>
    </Form>
  );
}
