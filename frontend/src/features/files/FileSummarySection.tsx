import {
  AlertTriangle,
  Building2,
  CalendarClock,
  CheckSquare,
  FileText,
  ListChecks,
  RotateCcw,
  Sparkles,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useFileSummary, useGenerateFileSummary } from "@/hooks/useFiles";

interface FileSummarySectionProps {
  fileId: number;
}

interface SummaryListProps {
  icon: React.ReactNode;
  label: string;
  items: string[];
}

function SummaryList({ icon, label, items }: SummaryListProps) {
  if (items.length === 0) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-sm font-medium">
        {icon}
        {label}
      </div>
      <ul className="ml-1 list-inside list-disc space-y-1 text-sm text-muted-foreground">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function FileSummarySection({ fileId }: FileSummarySectionProps) {
  const { data: summary, isLoading } = useFileSummary(fileId);
  const generateSummary = useGenerateFileSummary();

  const handleGenerate = () => {
    generateSummary.mutate(fileId, {
      onError: (error) => {
        toast.error("Couldn't generate summary", {
          description: error instanceof Error ? error.message : undefined,
        });
      },
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
        <Spinner />
        Loading summary…
      </div>
    );
  }

  return (
    <div className="space-y-4 border-t pt-4">
      <div className="flex items-center justify-between">
        <h3 className="flex items-center gap-1.5 text-sm font-semibold">
          <Sparkles className="h-4 w-4 text-primary" />
          AI Summary
        </h3>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleGenerate}
          disabled={generateSummary.isPending}
        >
          {generateSummary.isPending ? (
            <Spinner className="mr-2" />
          ) : summary ? (
            <RotateCcw className="mr-2 h-3.5 w-3.5" />
          ) : (
            <Sparkles className="mr-2 h-3.5 w-3.5" />
          )}
          {generateSummary.isPending ? "Generating…" : summary ? "Regenerate" : "Generate Summary"}
        </Button>
      </div>

      {!summary && !generateSummary.isPending ? (
        <p className="text-sm text-muted-foreground">
          No summary yet. Generate one to get an executive summary, key points, important dates,
          people, organizations, risks, and action items — grounded only in this file's content.
        </p>
      ) : null}

      {summary ? (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-sm font-medium">
              <FileText className="h-3.5 w-3.5" />
              Executive Summary
            </div>
            <p className="text-sm text-muted-foreground">{summary.executive_summary}</p>
          </div>

          <SummaryList icon={<ListChecks className="h-3.5 w-3.5" />} label="Key Points" items={summary.key_points} />
          <SummaryList
            icon={<CalendarClock className="h-3.5 w-3.5" />}
            label="Important Dates"
            items={summary.important_dates}
          />
          <SummaryList icon={<Users className="h-3.5 w-3.5" />} label="People" items={summary.people} />
          <SummaryList
            icon={<Building2 className="h-3.5 w-3.5" />}
            label="Organizations"
            items={summary.organizations}
          />
          <SummaryList icon={<AlertTriangle className="h-3.5 w-3.5" />} label="Risks" items={summary.risks} />
          <SummaryList
            icon={<CheckSquare className="h-3.5 w-3.5" />}
            label="Action Items"
            items={summary.action_items}
          />
        </div>
      ) : null}
    </div>
  );
}
