"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders LLM output as proper markdown (bold, lists, code, etc.) with the
// quest theme — so answers never show raw "**" or "*" characters.
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="space-y-2 text-sm leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: (props) => <p className="text-quest-text/90" {...props} />,
          strong: (props) => <strong className="font-semibold text-quest-text" {...props} />,
          em: (props) => <em className="italic" {...props} />,
          ul: (props) => <ul className="list-disc space-y-1 pl-5" {...props} />,
          ol: (props) => <ol className="list-decimal space-y-1 pl-5" {...props} />,
          li: (props) => <li className="text-quest-text/90" {...props} />,
          h1: (props) => <h1 className="font-display text-lg font-bold" {...props} />,
          h2: (props) => <h2 className="font-display text-base font-bold" {...props} />,
          h3: (props) => <h3 className="font-display text-sm font-semibold" {...props} />,
          a: (props) => <a className="text-quest-cyan underline" target="_blank" rel="noreferrer" {...props} />,
          code: ({ className, children, ...props }) => {
            const inline = !className;
            return inline ? (
              <code className="rounded bg-quest-bg px-1.5 py-0.5 font-mono text-quest-lime" {...props}>
                {children}
              </code>
            ) : (
              <code className="font-mono" {...props}>{children}</code>
            );
          },
          pre: (props) => (
            <pre className="overflow-x-auto rounded-xl bg-quest-bg p-3 font-mono text-xs" {...props} />
          ),
          blockquote: (props) => (
            <blockquote className="border-l-2 border-quest-violet pl-3 text-quest-muted" {...props} />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
