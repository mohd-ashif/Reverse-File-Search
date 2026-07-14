import { FolderPlus, ScanSearch, FileStack, Search } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface Step {
  icon: LucideIcon;
  title: string;
  description: string;
}

const STEPS: Step[] = [
  {
    icon: FolderPlus,
    title: "1. Add a folder",
    description: "Point the app at a directory on the server's filesystem that you want to make searchable.",
  },
  {
    icon: ScanSearch,
    title: "2. Scan it",
    description: "Run a scan to extract text and generate embeddings for every file inside — this is what makes content searchable.",
  },
  {
    icon: FileStack,
    title: "3. Review files",
    description: "Track each file's status — Pending, Extracted, Indexed, or Failed — and inspect details for any that need attention.",
  },
  {
    icon: Search,
    title: "4. Search",
    description: "Query file contents in plain language and get ranked results with the matching passage highlighted.",
  },
];

export function GettingStarted() {
  return (
    <section aria-labelledby="getting-started-heading" className="space-y-4">
      <div>
        <h2 id="getting-started-heading" className="text-lg font-semibold tracking-tight">
          Welcome to Reverse File Search
        </h2>
        <p className="max-w-2xl text-sm text-muted-foreground">
          A semantic search engine for your files. Monitor folders, index their contents, and find what
          you need by meaning — not just by filename. Here's how it works, end to end.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map(({ icon: Icon, title, description }) => (
          <Card key={title}>
            <CardContent className="space-y-2 pt-6">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10">
                <Icon className="h-4.5 w-4.5 text-primary" aria-hidden="true" />
              </div>
              <p className="text-sm font-semibold">{title}</p>
              <p className="text-sm text-muted-foreground">{description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
