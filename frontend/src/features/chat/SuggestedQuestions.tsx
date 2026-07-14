import { Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "What are my most recently indexed files about?",
  "Summarize the key points across my documents.",
  "Find files that mention deadlines or dates.",
  "What files reference budget or financial figures?",
];

interface SuggestedQuestionsProps {
  onSelect: (question: string) => void;
}

export function SuggestedQuestions({ onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="mx-auto flex max-w-2xl flex-1 flex-col items-center justify-center gap-6 px-4 text-center">
      <div className="space-y-2">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Sparkles className="h-6 w-6 text-primary" />
        </div>
        <h2 className="text-xl font-semibold">Ask about your files</h2>
        <p className="text-sm text-muted-foreground">
          Chat with an AI grounded in the content of your indexed folders. Answers cite the files they come
          from — nothing is made up.
        </p>
      </div>

      <div className="grid w-full gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSelect(question)}
            className="rounded-lg border bg-card p-3 text-left text-sm transition-colors hover:border-primary/50 hover:bg-accent"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
