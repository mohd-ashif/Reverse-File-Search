import { UAParser } from "ua-parser-js";
import { Laptop, LogOut } from "lucide-react";

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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { useRevokeSession } from "@/hooks/useAuth";
import { formatDate } from "@/lib/status";
import type { Session } from "@/types/auth";

function describeUserAgent(userAgent: string | null): { browser: string; os: string } {
  if (!userAgent) {
    return { browser: "Unknown browser", os: "Unknown OS" };
  }
  const parsed = new UAParser(userAgent).getResult();
  const browser = [parsed.browser.name, parsed.browser.version].filter(Boolean).join(" ") || "Unknown browser";
  const os = [parsed.os.name, parsed.os.version].filter(Boolean).join(" ") || "Unknown OS";
  return { browser, os };
}

interface SessionCardProps {
  session: Session;
}

/**
 * Renders a single active session (one row per refresh-token family).
 *
 * KNOWN LIMITATION (backend, not this component): `GET /me/sessions` always
 * returns `is_current: false` for every session today — the access token
 * doesn't carry the refresh-token family id needed to identify "this"
 * session server-side (see `backend/app/api/v1/endpoints/me.py`). The
 * "Current session" badge below is wired correctly and will start working
 * the moment the backend starts sending a real value; until then it simply
 * never renders. Because of that unreliability, the "Log out" action is
 * intentionally offered on every session row (not just non-current ones).
 */
export function SessionCard({ session }: SessionCardProps) {
  const revokeSession = useRevokeSession();
  const { browser, os } = describeUserAgent(session.user_agent);

  const handleRevoke = () => {
    revokeSession.mutate(session.id);
  };

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-md bg-muted p-2">
            <Laptop className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium">
                {browser} on {os}
              </span>
              {session.is_current ? <Badge variant="success">Current session</Badge> : null}
            </div>
            <p className="text-xs text-muted-foreground">
              IP: {session.ip_address ?? "Unknown"}
            </p>
            <p className="text-xs text-muted-foreground">
              Created {formatDate(session.created_at)} &middot; Last active {formatDate(session.last_seen_at)}
            </p>
          </div>
        </div>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              className="self-start text-destructive hover:text-destructive sm:self-center"
              disabled={revokeSession.isPending}
              aria-label="Log out this session"
            >
              {revokeSession.isPending ? <Spinner className="mr-2" /> : <LogOut className="mr-2 h-4 w-4" />}
              Log out
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Log out this session?</AlertDialogTitle>
              <AlertDialogDescription>
                This will revoke the session on {browser} ({os}) and require signing in again from that device.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={handleRevoke}
              >
                Log out
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </CardContent>
    </Card>
  );
}
