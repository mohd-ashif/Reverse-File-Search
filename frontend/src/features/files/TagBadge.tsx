import { cn } from "@/lib/utils";
import { tagColorClasses } from "@/lib/tagColors";
import { tagIcon } from "@/lib/tagIcons";

interface TagBadgeProps {
  tag: string;
  className?: string;
}

export function TagBadge({ tag, className }: TagBadgeProps) {
  const Icon = tagIcon(tag);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-transparent px-2.5 py-0.5 text-xs font-semibold",
        tagColorClasses(tag),
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {tag}
    </span>
  );
}
