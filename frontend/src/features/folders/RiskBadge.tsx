import { cn } from "@/lib/utils";
import type { RiskAssessment } from "@/lib/folderRisk";

const RISK_CONFIG: Record<RiskAssessment["level"], { emoji: string; label: string; classes: string }> = {
  low: {
    emoji: "🟢",
    label: "LOW",
    classes: "border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300",
  },
  medium: {
    emoji: "🟡",
    label: "MEDIUM",
    classes: "border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300",
  },
  high: {
    emoji: "🔴",
    label: "HIGH",
    classes: "border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300",
  },
};

interface RiskBadgeProps {
  assessment: RiskAssessment;
}

export function RiskBadge({ assessment }: RiskBadgeProps) {
  const config = RISK_CONFIG[assessment.level];

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("space-y-1.5 rounded-md border p-3 text-sm", config.classes)}
    >
      <p className="font-semibold">
        {config.emoji} Risk Level: {config.label}
      </p>
      <p>
        <span className="font-medium">Reason:</span> {assessment.reason}
      </p>
      <p>
        <span className="font-medium">Recommendation:</span> {assessment.recommendation}
      </p>
    </div>
  );
}
