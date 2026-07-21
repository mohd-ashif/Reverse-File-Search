import { useEffect } from "react";
import { AlertCircle, FileDiff, IndianRupee, ListTree, Minus, Plus } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useCompareFiles } from "@/hooks/useFiles";

export interface ComparePair {
  fileIdA: number;
  fileIdB: number;
}

interface CompareFilesDialogProps {
  pair: ComparePair | null;
  onOpenChange: (open: boolean) => void;
}

function Section({
  icon: Icon,
  title,
  items,
  className,
}: {
  icon: typeof Plus;
  title: string;
  items: string[];
  className: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="space-y-1.5">
      <h3 className="flex items-center gap-1.5 text-sm font-medium">
        <Icon className="h-4 w-4" />
        {title}
      </h3>
      <ul className="space-y-1">
        {items.map((item, index) => (
          <li key={index} className={`rounded-md border px-2.5 py-1.5 text-sm ${className}`}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CompareFilesDialog({ pair, onOpenChange }: CompareFilesDialogProps) {
  const { mutate, data, isPending, isError, error, reset } = useCompareFiles();

  useEffect(() => {
    if (pair) {
      mutate(pair);
    } else {
      reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pair]);

  return (
    <Dialog open={pair !== null} onOpenChange={(open) => !open && onOpenChange(false)}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileDiff className="h-5 w-5" />
            Compare files
          </DialogTitle>
          <DialogDescription>
            {data ? (
              <>
                <span className="font-mono text-xs">{data.file_a}</span> vs{" "}
                <span className="font-mono text-xs">{data.file_b}</span>
              </>
            ) : (
              "AI-generated comparison, grounded only in these two files' own content."
            )}
          </DialogDescription>
        </DialogHeader>

        {isPending ? (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-muted-foreground">
            <Spinner />
            Comparing files…
          </div>
        ) : isError ? (
          <div className="space-y-3 py-4">
            <div className="flex items-start gap-2.5 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <p>{error instanceof Error ? error.message : "Comparison failed."}</p>
            </div>
            <Button variant="outline" size="sm" onClick={() => pair && mutate(pair)}>
              Retry
            </Button>
          </div>
        ) : data ? (
          <div className="space-y-4 py-2">
            <p className="text-sm">{data.summary}</p>

            <Section
              icon={ListTree}
              title="Differences"
              items={data.differences}
              className="border-border bg-muted/40"
            />
            <Section
              icon={Plus}
              title="Added clauses"
              items={data.added_clauses}
              className="border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
            />
            <Section
              icon={Minus}
              title="Removed clauses"
              items={data.removed_clauses}
              className="border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
            />
            <Section
              icon={IndianRupee}
              title="Financial changes"
              items={data.financial_changes}
              className="border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300"
            />

            {data.differences.length === 0 &&
            data.added_clauses.length === 0 &&
            data.removed_clauses.length === 0 &&
            data.financial_changes.length === 0 ? (
              <p className="text-sm text-muted-foreground">No notable differences found.</p>
            ) : null}
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
