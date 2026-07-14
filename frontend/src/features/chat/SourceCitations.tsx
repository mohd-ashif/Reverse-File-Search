import { Badge } from "@/components/ui/badge";
import type { SearchResultItem } from "@/types/search";

interface SourceCitationsProps {
  sources: string[];
  results?: SearchResultItem[];
  onSelectFile: (fileId: number) => void;
}

export function SourceCitations({ sources, results, onSelectFile }: SourceCitationsProps) {
  if (sources.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5 pt-1">
      <span className="text-xs text-muted-foreground">Sources:</span>
      {sources.map((source) => {
        const fileId = results?.find((result) => result.filename === source)?.file_id;
        return fileId !== undefined ? (
          <button key={source} type="button" onClick={() => onSelectFile(fileId)} className="rounded-full">
            <Badge variant="secondary" className="cursor-pointer transition-colors hover:bg-secondary/70">
              {source}
            </Badge>
          </button>
        ) : (
          <Badge key={source} variant="secondary">
            {source}
          </Badge>
        );
      })}
    </div>
  );
}
