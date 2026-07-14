import { AlertTriangle, FileText, Files, HardDrive, ShieldAlert, Timer } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatBytes, formatDuration } from "@/lib/status";
import type { FolderEstimate } from "@/types/scan";

interface FolderEstimatePreviewProps {
  estimate: FolderEstimate;
}

interface StatProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

function Stat({ icon, label, value }: StatProps) {
  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 text-muted-foreground">{icon}</span>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-semibold">{value}</p>
      </div>
    </div>
  );
}

export function FolderEstimatePreview({ estimate }: FolderEstimatePreviewProps) {
  return (
    <Card>
      <CardContent className="grid grid-cols-2 gap-4 p-4">
        <Stat icon={<Files className="h-4 w-4" />} label="Estimated files" value={estimate.estimated_files.toLocaleString()} />
        <Stat
          icon={<FileText className="h-4 w-4" />}
          label="Supported"
          value={`${estimate.estimated_supported_files.toLocaleString()} (${estimate.unsupported_files.toLocaleString()} unsupported)`}
        />
        <Stat icon={<Timer className="h-4 w-4" />} label="Estimated time" value={formatDuration(estimate.approx_scan_seconds)} />
        <Stat icon={<HardDrive className="h-4 w-4" />} label="Storage" value={formatBytes(estimate.estimated_storage_bytes)} />
        {estimate.large_files_detected > 0 ? (
          <div className="col-span-2 flex items-start gap-2.5 rounded-md border border-amber-200 bg-amber-50 p-2.5 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="text-sm">
              {estimate.large_files_detected} large file{estimate.large_files_detected === 1 ? "" : "s"} detected (over{" "}
              {formatBytes(estimate.large_file_threshold_bytes)}) — these may take longer to process.
            </p>
          </div>
        ) : null}
        {estimate.sensitive_files_detected > 0 ? (
          <div className="col-span-2 flex items-start gap-2.5 rounded-md border border-destructive/30 bg-destructive/10 p-2.5 text-destructive">
            <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="text-sm">
              {estimate.sensitive_files_detected} potentially sensitive file
              {estimate.sensitive_files_detected === 1 ? "" : "s"} detected (e.g.{" "}
              {estimate.sensitive_file_samples.slice(0, 3).join(", ")}
              {estimate.sensitive_files_detected > 3 ? ", …" : ""}). These look like credentials or keys and are
              skipped by default when scanning.
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
