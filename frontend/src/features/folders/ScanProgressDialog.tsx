import { useEffect } from "react";
import { CheckCircle2, CircleDashed, Loader2, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { useScanSocket } from "@/hooks/useScanSocket";
import { cn } from "@/lib/utils";
import { SCAN_STAGE_LABEL, SCAN_STAGES } from "@/types/scan";

interface ScanProgressDialogProps {
  scanId: string | null;
  folderPath: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onFinished?: () => void;
}

function formatClock(seconds: number): string {
  const total = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(total / 60);
  const secs = total % 60;
  return `${minutes}:${secs.toString().padStart(2, "0")}`;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-muted/30 p-2.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-sm font-semibold tabular-nums">{value}</p>
    </div>
  );
}

export function ScanProgressDialog({ scanId, folderPath, open, onOpenChange, onFinished }: ScanProgressDialogProps) {
  const state = useScanSocket(scanId);

  useEffect(() => {
    if (state.status === "done") {
      onFinished?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.status]);

  const activeStageIndex = state.stage ? SCAN_STAGES.indexOf(state.stage) : -1;
  const isDoneOrRunning = state.status === "done" || state.status === "running";
  const progressPercent = state.filesTotal > 0 ? (state.filesProcessed / state.filesTotal) * 100 : state.status === "done" ? 100 : 0;
  const isIndeterminate = state.status === "connecting" || (state.status === "running" && state.filesTotal === 0);

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onOpenChange(false)}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {state.status === "done"
              ? "Scan complete"
              : state.status === "error"
                ? "Scan failed"
                : "Scanning folder…"}
          </DialogTitle>
          <DialogDescription className="break-all">{folderPath}</DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <ol className="space-y-2">
            {SCAN_STAGES.map((stageKey, index) => {
              const isDone = state.status === "done" || (isDoneOrRunning && activeStageIndex > index);
              const isActive = state.status === "running" && activeStageIndex === index;
              return (
                <li key={stageKey} className="flex items-center gap-2.5 text-sm">
                  {isDone ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                  ) : isActive ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
                  ) : (
                    <CircleDashed className="h-4 w-4 shrink-0 text-muted-foreground/40" />
                  )}
                  <span
                    className={cn(
                      isDone
                        ? "text-foreground"
                        : isActive
                          ? "font-medium text-foreground"
                          : "text-muted-foreground/60"
                    )}
                  >
                    {SCAN_STAGE_LABEL[stageKey]}
                  </span>
                </li>
              );
            })}
          </ol>

          {state.status === "error" ? (
            <div className="flex items-start gap-2.5 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{state.errorMessage ?? "Something went wrong during the scan."}</p>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Progress value={progressPercent} indeterminate={isIndeterminate} />
                <p className="h-4 truncate text-xs text-muted-foreground" title={state.currentFile ?? undefined}>
                  {state.status === "running" && state.currentFile ? state.currentFile : " "}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <Stat label="Processed" value={state.filesProcessed.toLocaleString()} />
                <Stat
                  label="Remaining"
                  value={(state.status === "done" ? 0 : state.filesRemaining).toLocaleString()}
                />
                <Stat label="Elapsed" value={formatClock(state.elapsedSeconds)} />
                <Stat
                  label="Est. remaining"
                  value={
                    state.status === "done"
                      ? "0:00"
                      : state.estimatedRemainingSeconds != null
                        ? formatClock(state.estimatedRemainingSeconds)
                        : "—"
                  }
                />
              </div>
            </>
          )}

          {state.status === "done" && state.summary ? (
            <div className="animate-fade-in space-y-3">
              <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
                <p className="font-medium">Success summary</p>
                <p className="mt-1">
                  +{state.summary.scan.added} added, {state.summary.scan.modified} modified,{" "}
                  {state.summary.scan.deleted} deleted · Indexed {state.summary.index.embedded}, extracted{" "}
                  {state.summary.index.extracted}
                  {state.summary.scan.skipped_sensitive > 0
                    ? `, ${state.summary.scan.skipped_sensitive} sensitive skipped`
                    : ""}
                </p>
              </div>

              {state.summary.failed_files.length > 0 ? (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                  <p className="font-medium">
                    {state.summary.failed_files.length} file{state.summary.failed_files.length === 1 ? "" : "s"}{" "}
                    failed
                  </p>
                  <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto text-xs">
                    {state.summary.failed_files.map((failure) => (
                      <li key={failure.path} className="truncate" title={`${failure.filename}: ${failure.error}`}>
                        <span className="font-medium">{failure.filename}</span> — {failure.error}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            {state.status === "done" || state.status === "error" ? "Close" : "Run in background"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
