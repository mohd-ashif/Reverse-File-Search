import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { useChangePassword, useSessions } from "@/hooks/useAuth";
import { passwordSchema } from "@/lib/passwordSchema";

const changePasswordSchema = z
  .object({
    current_password: z.string().min(1, "Current password is required"),
    new_password: passwordSchema,
    confirm_password: z.string().min(1, "Confirm your new password"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Passwords do not match",
    path: ["confirm_password"],
  });

type ChangePasswordValues = z.infer<typeof changePasswordSchema>;

function ChangePasswordCard() {
  const changePassword = useChangePassword();
  const form = useForm<ChangePasswordValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const onSubmit = (values: ChangePasswordValues) => {
    changePassword.mutate(
      { current_password: values.current_password, new_password: values.new_password },
      {
        onSuccess: () => {
          toast.success("Password changed");
          form.reset();
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === 401) {
            form.setError("current_password", { message: "Current password is incorrect" });
            return;
          }
          toast.error("Failed to change password", {
            description: error instanceof Error ? error.message : undefined,
          });
        },
      }
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Change password</CardTitle>
        <CardDescription>Choose a strong password you don't use anywhere else.</CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="current_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Current password</FormLabel>
                  <FormControl>
                    <Input type="password" autoComplete="current-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="new_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New password</FormLabel>
                  <FormControl>
                    <Input type="password" autoComplete="new-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirm_password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm new password</FormLabel>
                  <FormControl>
                    <Input type="password" autoComplete="new-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={changePassword.isPending}>
              {changePassword.isPending ? <Spinner className="mr-2" /> : null}
              Change password
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}

/**
 * Sessions split: the full session list (with per-session log-out) lives on
 * its own route/page, `SessionsPage` at `/security/sessions`, per the spec's
 * explicit call for a separate page. This card just shows a quick count plus
 * a link, so the two routes aren't duplicating the same list — `/security`
 * summarizes, `/security/sessions` is the full management view.
 */
function SessionsSummaryCard() {
  const { data: sessions, isLoading, isError, error, refetch } = useSessions();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Active sessions</CardTitle>
        <CardDescription>Devices and browsers currently signed in to your account.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <Skeleton className="h-6 w-40" />
        ) : isError ? (
          <ErrorState error={error} onRetry={() => void refetch()} />
        ) : (
          <p className="text-sm text-muted-foreground">
            {sessions && sessions.length > 0
              ? `${sessions.length} active session${sessions.length === 1 ? "" : "s"}.`
              : "No active sessions found."}
          </p>
        )}
        <Button variant="outline" asChild>
          <Link to="/security/sessions">Manage sessions</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

/**
 * KNOWN GAP (backend, not omitted by mistake): the plan's DB schema includes
 * a `login_history` table, but no `GET /me/login-history` (or similar)
 * endpoint exposes it to the authenticated user themselves — only
 * `/me/sessions` exists (see `backend/app/api/v1/endpoints/me.py`). A
 * "Login History" section is deliberately NOT included here since there is
 * no data source to back it; adding one would mean fabricating data. Flagging
 * this as a backend gap for a future phase rather than inventing fake rows.
 */
export function SecurityPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Security</h1>
        <p className="text-sm text-muted-foreground">Manage your password and active sessions.</p>
      </div>

      <ChangePasswordCard />
      <SessionsSummaryCard />
    </div>
  );
}
