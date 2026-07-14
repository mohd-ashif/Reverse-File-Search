import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/api/client";

interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export function ErrorState({ error, onRetry, className }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 py-16 text-center ${className ?? ""}`}
    >
      <AlertTriangle className="mb-2 h-10 w-10 text-destructive" aria-hidden="true" />
      <p className="text-sm font-medium text-destructive">{messageFor(error)}</p>
      {onRetry ? (
        <Button variant="outline" size="sm" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
