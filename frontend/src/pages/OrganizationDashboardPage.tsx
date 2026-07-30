import { Building2, HardDrive, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { useMembers } from "@/hooks/useOrganizations";
import { useOrganizationStore } from "@/store/organizationStore";

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** exponent).toFixed(1)} ${units[exponent]}`;
}

export function OrganizationDashboardPage() {
  const organization = useOrganizationStore((s) => s.organization);
  const { data: members, isLoading } = useMembers(organization?.id);

  if (!organization) {
    return (
      <EmptyState
        icon={Building2}
        title="No organization"
        description="Your account isn't a member of any organization yet."
      />
    );
  }

  const storageUsed = organization.storage_used_bytes ?? 0;
  const storageLimit = organization.storage_limit_bytes ?? 0;
  const storagePct = storageLimit > 0 ? (storageUsed / storageLimit) * 100 : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{organization.name}</h1>
        <p className="text-sm text-muted-foreground">Organization dashboard overview.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Members</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : <div className="text-2xl font-bold">{members?.length ?? 0}</div>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Plan</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Badge variant="secondary" className="capitalize">
              {organization.subscription_plan ?? "free"}
            </Badge>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Storage</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="space-y-2">
            <Progress value={storagePct} />
            <p className="text-xs text-muted-foreground">
              {formatBytes(storageUsed)} of {storageLimit > 0 ? formatBytes(storageLimit) : "unlimited"}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
