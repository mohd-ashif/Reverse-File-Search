import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Building2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { useUpdateOrganization } from "@/hooks/useOrganizations";
import { useOrganizationStore } from "@/store/organizationStore";

const settingsSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255),
  email: z.string().trim().email().optional().or(z.literal("")),
  phone: z.string().trim().max(32).optional().or(z.literal("")),
  website: z.string().trim().max(512).optional().or(z.literal("")),
  country: z.string().trim().max(64).optional().or(z.literal("")),
  timezone: z.string().trim().max(64).optional().or(z.literal("")),
  industry: z.string().trim().max(128).optional().or(z.literal("")),
});
type SettingsFormValues = z.infer<typeof settingsSchema>;

export function OrganizationSettingsPage() {
  const organization = useOrganizationStore((s) => s.organization);
  const updateOrganization = useUpdateOrganization(organization?.id ?? -1);

  const form = useForm<SettingsFormValues>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      name: organization?.name ?? "",
      email: organization?.email ?? "",
      phone: organization?.phone ?? "",
      website: organization?.website ?? "",
      country: organization?.country ?? "",
      timezone: organization?.timezone ?? "",
      industry: organization?.industry ?? "",
    },
  });

  useEffect(() => {
    if (organization) {
      form.reset({
        name: organization.name,
        email: organization.email ?? "",
        phone: organization.phone ?? "",
        website: organization.website ?? "",
        country: organization.country ?? "",
        timezone: organization.timezone ?? "",
        industry: organization.industry ?? "",
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organization?.id]);

  if (!organization) {
    return (
      <EmptyState
        icon={Building2}
        title="No organization"
        description="Your account isn't a member of any organization yet."
      />
    );
  }

  const onSubmit = (values: SettingsFormValues) => {
    updateOrganization.mutate(
      {
        name: values.name,
        email: values.email || null,
        phone: values.phone || null,
        website: values.website || null,
        country: values.country || null,
        timezone: values.timezone || undefined,
        industry: values.industry || null,
      },
      {
        onSuccess: () => toast.success("Organization settings updated"),
        onError: (e) => toast.error("Failed to update settings", { description: e instanceof Error ? e.message : undefined }),
      }
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Organization settings</h1>
        <p className="text-sm text-muted-foreground">Manage your organization's profile and preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Profile</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Company name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Email</FormLabel>
                    <FormControl>
                      <Input type="email" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="phone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Phone</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="website"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Website</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="country"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Country</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="timezone"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Timezone</FormLabel>
                    <FormControl>
                      <Input placeholder="UTC" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="industry"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Industry</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="sm:col-span-2">
                <Button type="submit" disabled={updateOrganization.isPending}>
                  {updateOrganization.isPending ? <Spinner className="mr-2" /> : null}
                  Save changes
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
}
