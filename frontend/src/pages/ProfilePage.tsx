import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { useMe, useUpdateMe } from "@/hooks/useAuth";
import { formatDate } from "@/lib/status";
import { useOrganizationStore } from "@/store/organizationStore";
import { usePermissionStore } from "@/store/permissionStore";
import { useRoleStore } from "@/store/roleStore";

const profileSchema = z.object({
  full_name: z.string().trim().max(200).optional().or(z.literal("")),
  first_name: z.string().trim().max(100).optional().or(z.literal("")),
  last_name: z.string().trim().max(100).optional().or(z.literal("")),
  phone: z.string().trim().max(32).optional().or(z.literal("")),
});

type ProfileFormValues = z.infer<typeof profileSchema>;

function initialsFor(name: string | null, email: string): string {
  const source = name?.trim() || email;
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}

export function ProfilePage() {
  const { data: user, isLoading, isError, error, refetch } = useMe();
  const updateMe = useUpdateMe();
  const organization = useOrganizationStore((s) => s.organization);
  const permissions = usePermissionStore((s) => s.permissions);
  const roles = useRoleStore((s) => s.roles);

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: "", first_name: "", last_name: "", phone: "" },
  });

  useEffect(() => {
    if (user) {
      form.reset({
        full_name: user.full_name ?? "",
        first_name: user.first_name ?? "",
        last_name: user.last_name ?? "",
        phone: user.phone ?? "",
      });
    }
    // Only re-sync when a fresh `user` object arrives from the server.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const onSubmit = (values: ProfileFormValues) => {
    updateMe.mutate(
      {
        full_name: values.full_name || undefined,
        first_name: values.first_name || undefined,
        last_name: values.last_name || undefined,
        phone: values.phone || undefined,
      },
      {
        onSuccess: () => toast.success("Profile updated"),
        onError: (err) => toast.error("Failed to update profile", {
          description: err instanceof Error ? err.message : undefined,
        }),
      }
    );
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (isError || !user) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
        <p className="text-sm text-muted-foreground">View and update your account details.</p>
      </div>

      <Card>
        <CardContent className="flex flex-col gap-4 pt-6 sm:flex-row sm:items-center">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt={user.full_name ?? user.email}
              className="h-16 w-16 rounded-full object-cover"
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-lg font-semibold text-primary-foreground">
              {initialsFor(user.full_name, user.email)}
            </div>
          )}
          <div className="space-y-1">
            <p className="text-lg font-semibold">{user.full_name || user.email}</p>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            <p className="text-xs text-muted-foreground">
              Last login: {user.last_login_at ? formatDate(user.last_login_at) : "Never"}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Organization</CardTitle>
          <CardDescription>
            {organization ? "The organization your account is a member of." : "You are not part of an organization."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {organization ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{organization.name}</p>
                <p className="text-xs text-muted-foreground">{organization.slug}</p>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link to="/organization">View organization</Link>
              </Button>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No organization assigned.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Permissions</CardTitle>
          <CardDescription>
            {roles.length > 0 ? `Role: ${roles.join(", ")}` : "Granted to your account."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {permissions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {permissions.map((permission) => (
                <Badge key={permission} variant="secondary">
                  {permission}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No permissions granted.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Edit profile</CardTitle>
          <CardDescription>Email cannot be changed here.</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="full_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Full name</FormLabel>
                    <FormControl>
                      <Input placeholder="Jane Doe" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="first_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>First name</FormLabel>
                      <FormControl>
                        <Input placeholder="Jane" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="last_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Last name</FormLabel>
                      <FormControl>
                        <Input placeholder="Doe" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone</FormLabel>
                    <FormControl>
                      <Input type="tel" placeholder="+1 555 000 0000" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <Button type="submit" disabled={updateMe.isPending}>
                {updateMe.isPending ? <Spinner className="mr-2" /> : null}
                Save changes
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Password</CardTitle>
          {/*
            De-duplication choice: the actual change-password FORM lives only
            on SecurityPage (`/security`) since the spec lists it under both
            Profile and Security and building it twice would mean two sources
            of truth for the same mutation/validation. Profile just links out.
          */}
          <CardDescription>Change your password from the Security page.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" asChild>
            <Link to="/security">Go to Security</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
