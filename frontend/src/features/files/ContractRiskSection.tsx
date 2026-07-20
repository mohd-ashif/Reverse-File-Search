import { AlertTriangle, CheckCircle2, ShieldAlert } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAnalyzeContractRisks } from "@/hooks/useFiles";
import { cn } from "@/lib/utils";

interface ContractRiskSectionProps {
  fileId: number;
}

export function ContractRiskSection({ fileId }: ContractRiskSectionProps) {
  const { mutate, data, isPending, isError, error } = useAnalyzeContractRisks();

  const handleAnalyze = () => {
    mutate(fileId, {
      onError: (err) => {
        toast.error("Couldn't analyze contract risks", {
          description: err instanceof Error ? err.message : undefined,
        });
      },
    });
  };

  const flaggedCount = data?.risks.filter((risk) => risk.present).length ?? 0;

  return (
    <div className="space-y-4 border-t pt-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-sm font-semibold">
          <ShieldAlert className="h-4 w-4 text-primary" />
          Contract Risk Analysis
        </h3>
        <Button type="button" variant="outline" size="sm" onClick={handleAnalyze} disabled={isPending}>
          {isPending ? <Spinner className="mr-2" /> : <ShieldAlert className="mr-2 h-3.5 w-3.5" />}
          {isPending ? "Analyzing…" : data ? "Re-analyze" : "Analyze Risks"}
        </Button>
      </div>

      {!data && !isPending && !isError ? (
        <p className="text-sm text-muted-foreground">
          Checks for missing signatures, unlimited liability, auto-renewal, late fees, and termination
          clauses — explained in plain language, grounded only in this file's content.
        </p>
      ) : null}

      {isError && !isPending ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Contract risk analysis failed."}
        </p>
      ) : null}

      {data ? (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {flaggedCount > 0
              ? `${flaggedCount} of ${data.risks.length} risk${flaggedCount === 1 ? "" : "s"} flagged`
              : "No risks flagged"}
          </p>
          <ul className="space-y-2">
            {data.risks.map((risk) => (
              <li
                key={risk.risk}
                className={cn(
                  "rounded-md border p-2.5",
                  risk.present
                    ? "border-destructive/30 bg-destructive/10"
                    : "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/40"
                )}
              >
                <div className="flex items-center gap-1.5 text-sm font-medium">
                  {risk.present ? (
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-destructive" />
                  ) : (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  )}
                  {risk.risk}
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{risk.explanation}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
