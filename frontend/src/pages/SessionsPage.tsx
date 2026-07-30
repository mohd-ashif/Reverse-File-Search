import { Link } from "react-router-dom";
import { ArrowLeft, MonitorSmartphone } from "lucide-react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { SessionCard } from "@/components/auth/SessionCard";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useRevokeSession, useSessions } from "@/hooks/useAuth";

function LogoutAllButton() {
  const { data: sessions } = useSessions();
  const revokeSession = useRevokeSession();

  const handleLogoutAll = () => {
    const ids = sessions?.map((s) => s.id) ?? [];
    // Simple sequential/parallel fan-out — each mutation independently
    // invalidates the sessions query on success. Not worth a bulk-mutation
    // abstraction for what's just an array of individual DELETE calls.
    ids.forEach((id) => revokeSession.mutate(id));
    toast.success("Logging out all sessions");
  };

  if (!sessions || sessions.length === 0) {
    return null;
  }

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="outline" className="text-destructive hover:text-destructive">
          Log out all sessions
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Log out all sessions?</AlertDialogTitle>
          <AlertDialogDescription>
            This revokes every active session listed below, including this one if it's among them. You'll need to
            sign in again.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={handleLogoutAll}
          >
            Log out all
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function SessionsPage() {
  const { data: sessions, isLoading, isError, error, refetch } = useSessions();

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Button variant="ghost" size="sm" className="-ml-2 mb-1" asChild>
            <Link to="/security">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Security
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold tracking-tight">Active sessions</h1>
          <p className="text-sm text-muted-foreground">
            These are the devices currently signed in to your account. Log out any you don't recognize.
          </p>
        </div>
        <LogoutAllButton />
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState error={error} onRetry={() => void refetch()} />
      ) : sessions && sessions.length > 0 ? (
        <div className="space-y-3">
          {sessions.map((session) => (
            <SessionCard key={session.id} session={session} />
          ))}
        </div>
      ) : (
        <EmptyState
          icon={MonitorSmartphone}
          title="No active sessions"
          description="You currently have no active sessions on record."
        />
      )}
    </div>
  );
}

