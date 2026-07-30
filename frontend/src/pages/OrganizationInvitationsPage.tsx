import { useRef, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Mail, Upload } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

import { ApiError } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useInvitations, useInviteMember, useResendInvitation, useRevokeInvitation } from "@/hooks/useOrganizations";
import { formatDate } from "@/lib/status";
import { useOrganizationStore } from "@/store/organizationStore";
import type { InvitationStatus } from "@/types/organization";

const ROLES = ["Organization Admin", "Manager", "Employee", "Viewer"] as const;

const inviteSchema = z.object({
  email: z.string().email("Enter a valid email address"),
  role: z.enum(ROLES),
});
type InviteFormValues = z.infer<typeof inviteSchema>;

function statusVariant(status: InvitationStatus): "success" | "warning" | "secondary" | "destructive" {
  switch (status) {
    case "accepted":
      return "success";
    case "pending":
      return "warning";
    case "expired":
      return "secondary";
    case "revoked":
      return "destructive";
  }
}

function InviteForm({ organizationId }: { organizationId: number }) {
  const inviteMember = useInviteMember(organizationId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [bulkResult, setBulkResult] = useState<string | null>(null);

  const form = useForm<InviteFormValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: { email: "", role: "Employee" },
  });

  const onSubmit = (values: InviteFormValues) => {
    inviteMember.mutate(values, {
      onSuccess: () => {
        toast.success(`Invitation sent to ${values.email}`);
        form.reset({ email: "", role: values.role });
      },
      onError: (e) => {
        const description =
          e instanceof ApiError && e.status === 409 ? "An invitation is already pending for that email." : undefined;
        toast.error("Failed to send invitation", { description: description ?? (e instanceof Error ? e.message : undefined) });
      },
    });
  };

  const handleCsvUpload = async (file: File) => {
    const text = await file.text();
    const rows = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => line.split(","));

    let succeeded = 0;
    let failed = 0;
    for (const [email, role] of rows) {
      const parsed = inviteSchema.safeParse({ email: email?.trim(), role: (role?.trim() as string) || "Employee" });
      if (!parsed.success) {
        failed += 1;
        continue;
      }
      try {
        await inviteMember.mutateAsync(parsed.data);
        succeeded += 1;
      } catch {
        failed += 1;
      }
    }
    setBulkResult(`Sent ${succeeded} invitation(s), ${failed} failed.`);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Invite a member</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormLabel>Email</FormLabel>
                  <FormControl>
                    <Input type="email" placeholder="teammate@company.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="role"
              render={({ field }) => (
                <FormItem className="w-full sm:w-48">
                  <FormLabel>Role</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {ROLES.map((role) => (
                        <SelectItem key={role} value={role}>
                          {role}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />
            <Button type="submit" disabled={inviteMember.isPending}>
              {inviteMember.isPending ? <Spinner className="mr-2" /> : <Mail className="mr-2 h-4 w-4" />}
              Send invite
            </Button>
          </form>
        </Form>

        <div className="flex items-center gap-3 border-t pt-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mr-2 h-4 w-4" />
            Bulk invite (CSV)
          </Button>
          <span className="text-xs text-muted-foreground">Format: email,role — one per line</span>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void handleCsvUpload(file);
              e.target.value = "";
            }}
          />
        </div>
        {bulkResult && <p className="text-sm text-muted-foreground">{bulkResult}</p>}
      </CardContent>
    </Card>
  );
}

export function OrganizationInvitationsPage() {
  const organization = useOrganizationStore((s) => s.organization);
  const orgId = organization?.id;
  const { data: invitations, isLoading, isError, error, refetch } = useInvitations(orgId);
  const resendInvitation = useResendInvitation(orgId ?? -1);
  const revokeInvitation = useRevokeInvitation(orgId ?? -1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Invitations</h1>
        <p className="text-sm text-muted-foreground">Invite new members and track pending invitations.</p>
      </div>

      {orgId && <InviteForm organizationId={orgId} />}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : invitations && invitations.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Expires</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invitations.map((invitation) => (
              <TableRow key={invitation.id}>
                <TableCell>{invitation.email}</TableCell>
                <TableCell>{invitation.role}</TableCell>
                <TableCell>
                  <Badge variant={statusVariant(invitation.status)} className="capitalize">
                    {invitation.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(invitation.expires_at)}</TableCell>
                <TableCell className="text-right space-x-2">
                  {invitation.status === "pending" && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          resendInvitation.mutate(invitation.id, {
                            onSuccess: () => toast.success("Invitation resent"),
                          })
                        }
                      >
                        Resend
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-destructive hover:text-destructive"
                        onClick={() => revokeInvitation.mutate(invitation.id)}
                      >
                        Revoke
                      </Button>
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <EmptyState icon={Mail} title="No invitations" description="Invitations you send will appear here." />
      )}
    </div>
  );
}
