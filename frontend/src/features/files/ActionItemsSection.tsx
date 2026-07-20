import { useState } from "react";
import { CalendarClock, ListTodo, User } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useExtractActionItems } from "@/hooks/useFiles";
import { cn } from "@/lib/utils";
import type { ActionItemPriority } from "@/types/actionItems";

interface ActionItemsSectionProps {
  fileId: number;
}

const PRIORITY_VARIANT: Record<ActionItemPriority, "destructive" | "warning" | "secondary"> = {
  High: "destructive",
  Medium: "warning",
  Low: "secondary",
};

export function ActionItemsSection({ fileId }: ActionItemsSectionProps) {
  const { mutate, data, isPending, isError, error } = useExtractActionItems();
  const [checked, setChecked] = useState<Set<number>>(new Set());

  const handleExtract = () => {
    setChecked(new Set());
    mutate(fileId, {
      onError: (err) => {
        toast.error("Couldn't extract action items", {
          description: err instanceof Error ? err.message : undefined,
        });
      },
    });
  };

  const toggleChecked = (index: number) => {
    setChecked((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div className="space-y-4 border-t pt-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-sm font-semibold">
          <ListTodo className="h-4 w-4 text-primary" />
          Action Items
        </h3>
        <Button type="button" variant="outline" size="sm" onClick={handleExtract} disabled={isPending}>
          {isPending ? <Spinner className="mr-2" /> : <ListTodo className="mr-2 h-3.5 w-3.5" />}
          {isPending ? "Extracting…" : data ? "Re-extract" : "Extract Action Items"}
        </Button>
      </div>

      {!data && !isPending && !isError ? (
        <p className="text-sm text-muted-foreground">
          Pulls out who owes what, by when, and how urgent it is — e.g. from meeting notes — grounded only
          in this file's content.
        </p>
      ) : null}

      {isError && !isPending ? (
        <p className="text-sm text-destructive">
          {error instanceof Error ? error.message : "Action item extraction failed."}
        </p>
      ) : null}

      {data ? (
        data.action_items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No action items found in this file.</p>
        ) : (
          <ul className="space-y-2">
            {data.action_items.map((item, index) => (
              <li key={index} className="flex items-start gap-2.5 rounded-md border p-2.5">
                <input
                  type="checkbox"
                  checked={checked.has(index)}
                  onChange={() => toggleChecked(index)}
                  aria-label={`Mark "${item.task}" done`}
                  className="mt-0.5 h-4 w-4 accent-primary"
                />
                <div className="min-w-0 flex-1 space-y-1">
                  <p className={cn("text-sm", checked.has(index) && "text-muted-foreground line-through")}>
                    {item.task}
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge variant={PRIORITY_VARIANT[item.priority]}>{item.priority}</Badge>
                    {item.person ? (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <User className="h-3 w-3" />
                        {item.person}
                      </span>
                    ) : null}
                    {item.deadline ? (
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <CalendarClock className="h-3 w-3" />
                        {item.deadline}
                      </span>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}
