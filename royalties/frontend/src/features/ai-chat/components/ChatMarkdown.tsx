/** ChatMarkdown — premium markdown renderer for AI chat responses.
 *  Syntax-highlighted code blocks with language labels, image rendering,
 *  and responsive compact/full variants. */

import { useState, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Copy, Check, ExternalLink, FileCode2, ImageIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

/* ─── Language display names ──────────────────────────── */
const LANG_LABELS: Record<string, string> = {
  js: 'JavaScript',
  javascript: 'JavaScript',
  ts: 'TypeScript',
  typescript: 'TypeScript',
  tsx: 'TSX',
  jsx: 'JSX',
  py: 'Python',
  python: 'Python',
  sql: 'SQL',
  json: 'JSON',
  html: 'HTML',
  css: 'CSS',
  bash: 'Bash',
  sh: 'Shell',
  shell: 'Shell',
  yml: 'YAML',
  yaml: 'YAML',
  xml: 'XML',
  markdown: 'Markdown',
  md: 'Markdown',
  csv: 'CSV',
  diff: 'Diff',
  plaintext: 'Text',
  text: 'Text',
}

function langLabel(className?: string): string | null {
  if (!className) return null
  const match = className.match(/language-(\w+)/)
  if (!match) return null
  const lang = match[1].toLowerCase()
  return LANG_LABELS[lang] || lang.toUpperCase()
}

/* ─── Copy button for code blocks ─────────────────────── */
function CopyCodeButton({ text, compact }: { text: string; compact?: boolean }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [text])

  return (
    <button
      onClick={handleCopy}
      className={cn(
        'flex items-center gap-1 rounded-md border border-border/50 text-muted-foreground hover:text-foreground hover:bg-muted transition-all',
        'opacity-0 group-hover/code:opacity-100 focus:opacity-100',
        compact ? 'p-1' : 'px-2 py-1 text-[10px]',
      )}
      aria-label={copied ? 'Copied' : 'Copy code'}
    >
      {copied ? (
        <>
          <Check className="h-3 w-3 text-emerald-400" />
          {!compact && <span className="text-emerald-400">Copied</span>}
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          {!compact && <span>Copy</span>}
        </>
      )}
    </button>
  )
}

/* ─── Image renderer with lightbox feel ───────────────── */
function ChatImage({ src, alt }: { src?: string; alt?: string }) {
  const [error, setError] = useState(false)
  const [loaded, setLoaded] = useState(false)

  if (!src || error) {
    return (
      <div className="inline-flex items-center gap-2 rounded-lg border border-border/50 bg-muted/30 px-3 py-2 text-xs text-muted-foreground my-2">
        <ImageIcon className="h-4 w-4" />
        <span>{alt || 'Image unavailable'}</span>
      </div>
    )
  }

  return (
    <figure className="my-3">
      <a href={src} target="_blank" rel="noopener noreferrer" className="group/img relative block">
        <img
          src={src}
          alt={alt || ''}
          onError={() => setError(true)}
          onLoad={() => setLoaded(true)}
          className={cn(
            'max-w-full rounded-xl border border-border/50 shadow-sm transition-all',
            'hover:shadow-md hover:border-primary/30',
            loaded ? 'opacity-100' : 'opacity-0',
          )}
          style={{ maxHeight: 400 }}
        />
        {!loaded && <div className="absolute inset-0 rounded-xl bg-muted/50 animate-pulse" />}
        <div className="absolute top-2 right-2 opacity-0 group-hover/img:opacity-100 transition-opacity">
          <div className="p-1.5 rounded-md bg-background/80 border border-border/50 text-muted-foreground">
            <ExternalLink className="h-3 w-3" />
          </div>
        </div>
      </a>
      {alt && alt !== '' && (
        <figcaption className="mt-1.5 text-[11px] text-muted-foreground/70 text-center italic">
          {alt}
        </figcaption>
      )}
    </figure>
  )
}

/* ─── Main component ──────────────────────────────────── */
interface ChatMarkdownProps {
  content: string
  variant?: 'compact' | 'full'
  className?: string
}

export function ChatMarkdown({ content, variant = 'full', className }: ChatMarkdownProps) {
  const isCompact = variant === 'compact'

  return (
    <div className={cn('chat-markdown', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          p: ({ children }) => (
            <p className={cn('last:mb-0 leading-relaxed', isCompact ? 'mb-2' : 'mb-3')}>
              {children}
            </p>
          ),
          h1: ({ children }) => (
            <h1
              className={cn(
                'font-bold first:mt-0 text-foreground',
                isCompact ? 'text-sm mb-2 mt-3' : 'text-lg mb-3 mt-4',
              )}
            >
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2
              className={cn(
                'font-semibold first:mt-0 text-foreground',
                isCompact ? 'text-sm mb-1.5 mt-2' : 'text-base mb-2 mt-3',
              )}
            >
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3
              className={cn(
                'font-semibold first:mt-0 text-foreground',
                isCompact ? 'text-xs mb-1 mt-2' : 'text-sm mb-2 mt-3',
              )}
            >
              {children}
            </h3>
          ),
          ul: ({ children }) => (
            <ul
              className={cn(
                'list-disc marker:text-primary/50',
                isCompact ? 'mb-2 ml-3 space-y-0.5' : 'mb-3 ml-4 space-y-1',
              )}
            >
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol
              className={cn(
                'list-decimal marker:text-primary/50',
                isCompact ? 'mb-2 ml-3 space-y-0.5' : 'mb-3 ml-4 space-y-1',
              )}
            >
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          em: ({ children }) => <em className="italic text-muted-foreground">{children}</em>,
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline underline-offset-2 decoration-primary/30 hover:decoration-primary transition-colors"
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote
              className={cn(
                'border-l-2 border-primary/30 text-muted-foreground italic',
                isCompact ? 'pl-3 my-2' : 'pl-4 my-3',
              )}
            >
              {children}
            </blockquote>
          ),
          img: ({ src, alt }) => <ChatImage src={src} alt={alt} />,
          code: ({ className: codeClassName, children }) => {
            const isBlock = codeClassName?.includes('language-') || codeClassName?.includes('hljs')
            if (isBlock) {
              const text = String(children).replace(/\n$/, '')
              const label = langLabel(codeClassName)
              return (
                <div className={cn('group/code relative', isCompact ? 'my-2' : 'my-3')}>
                  {/* Header bar with language + copy */}
                  <div
                    className={cn(
                      'flex items-center justify-between rounded-t-lg border border-b-0 border-border/50 bg-muted/60',
                      isCompact ? 'px-3 py-1' : 'px-4 py-1.5',
                    )}
                  >
                    <div className="flex items-center gap-1.5 text-muted-foreground">
                      <FileCode2 className={cn(isCompact ? 'h-2.5 w-2.5' : 'h-3 w-3')} />
                      {label && (
                        <span
                          className={cn('font-medium', isCompact ? 'text-[9px]' : 'text-[11px]')}
                        >
                          {label}
                        </span>
                      )}
                    </div>
                    <CopyCodeButton text={text} compact={isCompact} />
                  </div>
                  <pre
                    className={cn(
                      'overflow-x-auto rounded-b-lg border border-border/50 font-mono leading-relaxed bg-[--code-bg,theme(colors.background/80%)]',
                      isCompact ? 'p-3 text-[10px]' : 'p-4 text-xs',
                    )}
                  >
                    <code className={codeClassName}>{children}</code>
                  </pre>
                </div>
              )
            }
            return (
              <code
                className={cn(
                  'rounded bg-primary/10 text-primary text-[0.85em] font-mono',
                  isCompact ? 'px-1 py-0.5' : 'px-1.5 py-0.5 rounded-md',
                )}
              >
                {children}
              </code>
            )
          },
          pre: ({ children }) => <>{children}</>,
          table: ({ children }) => (
            <div
              className={cn(
                'overflow-x-auto rounded-lg border border-border/50',
                isCompact ? 'my-2' : 'my-3',
              )}
            >
              <table className={cn('w-full', isCompact ? 'text-[10px]' : 'text-xs')}>
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/50 border-b border-border/50">{children}</thead>
          ),
          th: ({ children }) => (
            <th
              className={cn(
                'text-left font-semibold text-foreground',
                isCompact ? 'px-2 py-1' : 'px-3 py-2',
              )}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              className={cn(
                'border-t border-border/30 text-muted-foreground',
                isCompact ? 'px-2 py-1' : 'px-3 py-2',
              )}
            >
              {children}
            </td>
          ),
          hr: () => <hr className="my-4 border-border/30" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
