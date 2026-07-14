import { useState } from "react";
import { Check, Copy } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

function CodeBlock({ className, children }: { className?: string; children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const language = /language-(\w+)/.exec(className ?? "")?.[1];
  const text = String(children).replace(/\n$/, "");

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access denied — nothing actionable to do here.
    }
  };

  return (
    <div className="group relative my-2 overflow-hidden rounded-md border bg-muted/50">
      <div className="flex items-center justify-between border-b bg-muted px-3 py-1.5">
        <span className="text-xs font-medium text-muted-foreground">{language ?? "code"}</span>
        <button
          type="button"
          onClick={() => void handleCopy()}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-muted-foreground opacity-0 transition-opacity hover:bg-accent hover:text-accent-foreground group-hover:opacity-100"
          aria-label="Copy code"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 text-xs leading-relaxed">
        <code className={className}>{text}</code>
      </pre>
    </div>
  );
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div
      className={cn(
        "prose prose-sm max-w-none break-words dark:prose-invert",
        "prose-p:leading-relaxed prose-pre:m-0 prose-pre:bg-transparent prose-pre:p-0",
        "prose-code:before:content-none prose-code:after:content-none",
        className
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ children, node: _node, ...props }) => (
            <a {...props} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
          code({ className: codeClassName, children, node: _node, ...rest }) {
            const isInline = !/language-/.test(codeClassName ?? "");
            if (isInline) {
              return (
                <code className={cn("rounded bg-muted px-1 py-0.5 text-[0.85em]", codeClassName)} {...rest}>
                  {children}
                </code>
              );
            }
            return <CodeBlock className={codeClassName}>{children}</CodeBlock>;
          },
          pre({ children }) {
            return <>{children}</>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
