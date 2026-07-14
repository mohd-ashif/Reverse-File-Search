import type { FileIndexStatus } from "@/types/file";
import type { BadgeProps } from "@/components/ui/badge";

export const FILE_STATUS_LABEL: Record<FileIndexStatus, string> = {
  pending: "Pending",
  extracted: "Extracted",
  embedded: "Indexed",
  failed: "Failed",
};

export const FILE_STATUS_VARIANT: Record<FileIndexStatus, NonNullable<BadgeProps["variant"]>> = {
  pending: "secondary",
  extracted: "warning",
  embedded: "success",
  failed: "destructive",
};

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  return `${exponent === 0 ? value : value.toFixed(1)} ${units[exponent]}`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))} seconds`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"}`;
  const hours = Math.round(minutes / 6) / 10;
  return `${hours} hour${hours === 1 ? "" : "s"}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
