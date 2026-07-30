import { MoreHorizontal, Users } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  useChangeMemberRole,
  useMembers,
  useRemoveMember,
  useSuspendMember,
} from "@/hooks/useOrganizations";
import { formatDate } from "@/lib/status";
import { useOrganizationStore } from "@/store/organizationStore";
import type { MemberStatus } from "@/types/organization";

const ASSIGNABLE_ROLES = ["Organization Admin", "Manager", "Employee", "Viewer"];

function statusVariant(status: MemberStatus): "success" | "warning" | "secondary" | "default" {
  switch (status) {
    case "joined":
      return "success";
    case "invited":
      return "warning";
    case "suspended":
      return "secondary";
    case "owner":
      return "default";
  }
}

export function OrganizationMembersPage() {
  const organization = useOrganizationStore((s) => s.organization);
  const orgId = organization?.id;
  const { data: members, isLoading, isError, error, refetch } = useMembers(orgId);
  const changeRole = useChangeMemberRole(orgId ?? -1);
  const removeMember = useRemoveMember(orgId ?? -1);
  const suspendMember = useSuspendMember(orgId ?? -1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Members</h1>
        <p className="text-sm text-muted-foreground">Manage who belongs to {organization?.name ?? "your organization"}.</p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : members && members.length > 0 ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {members.map((member) => (
              <TableRow key={member.id}>
                <TableCell className="flex items-center gap-2">
                  {member.user.avatar_url ? (
                    <img src={member.user.avatar_url} alt="" className="h-6 w-6 rounded-full object-cover" />
                  ) : (
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-[10px] font-semibold text-primary-foreground">
                      {(member.user.full_name || member.user.email).slice(0, 1).toUpperCase()}
                    </div>
                  )}
                  {member.user.full_name || "—"}
                </TableCell>
                <TableCell className="text-muted-foreground">{member.user.email}</TableCell>
                <TableCell>
                  {member.status === "owner" ? (
                    <Badge>Owner</Badge>
                  ) : (
                    <Select
                      value={member.role ?? undefined}
                      onValueChange={(role) =>
                        changeRole.mutate(
                          { memberId: member.id, role },
                          {
                            onSuccess: () => toast.success("Role updated"),
                            onError: (e) => toast.error("Failed to update role", { description: e instanceof Error ? e.message : undefined }),
                          }
                        )
                      }
                    >
                      <SelectTrigger className="h-8 w-40">
                        <SelectValue placeholder="No role" />
                      </SelectTrigger>
                      <SelectContent>
                        {ASSIGNABLE_ROLES.map((role) => (
                          <SelectItem key={role} value={role}>
                            {role}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </TableCell>
                <TableCell>
                  <Badge variant={statusVariant(member.status)} className="capitalize">
                    {member.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-muted-foreground">{formatDate(member.created_at)}</TableCell>
                <TableCell className="text-right">
                  {member.status !== "owner" && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        {member.status !== "suspended" && (
                          <DropdownMenuItem onClick={() => suspendMember.mutate(member.id)}>
                            Suspend
                          </DropdownMenuItem>
                        )}
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => removeMember.mutate(member.id)}
                        >
                          Remove
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <EmptyState icon={Users} title="No members yet" description="Invite people to get started." />
      )}
    </div>
  );
}
