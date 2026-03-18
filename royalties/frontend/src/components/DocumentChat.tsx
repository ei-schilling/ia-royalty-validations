/** Document-context chat — compact AI assistant with document injected as context. */

import { useState, useRef, useEffect, useCallback, useMemo, type FormEvent } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Send, Bot, User, Eraser, StopCircle, Copy, Check, ArrowDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat, fetchServerSentEvents } from '@tanstack/ai-react'
import { cn } from '@/lib/utils'

/* ─── Copy button for code blocks ────────────────────── */
function CopyBtn({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }}
      className="absolute top-2 right-2 p-1 rounded bg-background/80 border border-border/50 text-muted-foreground hover:text-foreground transition-all opacity-0 group-hover/pre:opacity-100"
    >
      {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
    </button>
  )
}

/* ─── Markdown renderer ──────────────────────────────── */
function Md({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        h1: ({ children }) => (
          <h1 className="text-sm font-bold mb-2 mt-3 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-sm font-semibold mb-1.5 mt-2 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-xs font-semibold mb-1 mt-2 first:mt-0">{children}</h3>
        ),
        ul: ({ children }) => (
          <ul className="mb-2 ml-3 space-y-0.5 list-disc marker:text-primary/50">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-2 ml-3 space-y-0.5 list-decimal marker:text-primary/50">{children}</ol>
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
          <blockquote className="border-l-2 border-primary/30 pl-3 my-2 text-muted-foreground italic">
            {children}
          </blockquote>
        ),
        code: ({ className, children }) => {
          const isBlock = className?.includes('language-')
          if (isBlock) {
            const text = String(children).replace(/\n$/, '')
            return (
              <div className="group/pre relative my-2">
                <pre className="overflow-x-auto rounded-lg bg-background/80 border border-border/50 p-3 text-[10px] font-mono leading-relaxed">
                  <code className={className}>{children}</code>
                </pre>
                <CopyBtn text={text} />
              </div>
            )
          }
          return (
            <code className="px-1 py-0.5 rounded bg-primary/10 text-primary text-[0.85em] font-mono">
              {children}
            </code>
          )
        },
        pre: ({ children }) => <>{children}</>,
        table: ({ children }) => (
          <div className="my-2 overflow-x-auto rounded-lg border border-border/50">
            <table className="w-full text-[10px]">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-muted/50 border-b border-border/50">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-2 py-1 text-left font-semibold text-foreground">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-2 py-1 border-t border-border/30 text-muted-foreground">{children}</td>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

/* ─── Suggestions for document analysis ──────────────── */
const DOC_SUGGESTIONS = [
  'Summarize the key data in this document',
  'Are there any anomalies or errors?',
  'What royalty rates are used?',
  'List all unique ISBNs or product identifiers',
]

/* ─── Props ──────────────────────────────────────────── */
interface Props {
  /** Raw text content of the document (injected as context). */
  documentContent: string
  /** Filename for display/context. */
  filename: string
}

export default function DocumentChat({ documentContent, filename }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const documentInjected = useRef(false)

  // Use query mode so it also has RAG access to the knowledge base
  const connection = useMemo(() => fetchServerSentEvents('/api/chat/stream?mode=query'), [])

  const { messages, sendMessage, isLoading, stop, clear } = useChat({ connection })

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > 60)
  }, [])

  /** Build a message that includes document context (first message only). */
  function sendWithContext(text: string) {
    if (!documentInjected.current && documentContent) {
      // Truncate to 400k chars to be safe with context window
      const docSlice = documentContent.slice(0, 400_000)
      const contextMessage =
        `The user is viewing a royalty statement file named "${filename}". ` +
        `Here is the full content of the document:\n\n` +
        `--- Document: ${filename} ---\n${docSlice}\n--- End of ${filename} ---\n\n` +
        `Please answer the following question based primarily on this document. ` +
        `If the information in the document is not sufficient, you may use your knowledge base (RAG) about royalty settlements to enrich your answer.\n\n` +
        `User question: ${text}`
      documentInjected.current = true
      sendMessage(contextMessage)
    } else {
      sendMessage(text)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const value = inputRef.current?.value.trim()
    if (!value || isLoading) return
    sendWithContext(value)
    if (inputRef.current) inputRef.current.value = ''
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  function handleInput() {
    if (!inputRef.current) return
    inputRef.current.style.height = 'auto'
    inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 100) + 'px'
  }

  function handleClear() {
    clear()
    documentInjected.current = false
  }

  const hasMessages = messages.length > 0

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50 shrink-0">
        <div className="w-5 h-5 rounded-md bg-primary/10 flex items-center justify-center">
          <Bot className="h-3 w-3 text-primary" />
        </div>
        <span className="text-xs font-medium text-foreground flex-1">Document Assistant</span>
        {hasMessages && (
          <button
            onClick={handleClear}
            className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            title="Clear chat"
          >
            <Eraser className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Messages area */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto min-h-0 scroll-smooth"
      >
        {!hasMessages ? (
          <div className="flex flex-col items-center justify-center h-full px-4 py-6">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <p className="text-xs text-muted-foreground text-center mb-4 max-w-[200px]">
              Ask questions about <span className="font-medium text-foreground">{filename}</span>
            </p>
            <div className="space-y-1.5 w-full">
              {DOC_SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendWithContext(s)}
                  className="w-full text-left text-[11px] px-3 py-2 rounded-lg border border-border/40 bg-card/50 hover:bg-card hover:border-primary/30 transition-all text-muted-foreground hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="px-3 py-3 space-y-2">
            <AnimatePresence initial={false}>
              {messages.map((msg) => {
                const isUser = msg.role === 'user'
                const textParts = msg.parts?.filter((p: { type: string }) => p.type === 'text')
                const rawText =
                  textParts
                    ?.map((p: { type: string; content?: string }) => p.content || '')
                    .join('') || ''
                if (!rawText) return null

                // Clean document injection from user display
                let displayText = rawText
                if (isUser && rawText.includes('--- Document:')) {
                  const match = rawText.match(/User question:\s*(.+)$/s)
                  displayText =
                    match?.[1]?.trim() ||
                    rawText
                      .replace(/[\s\S]*--- End of .+? ---[\s\S]*?User question:\s*/s, '')
                      .trim()
                  if (!displayText) displayText = '(Document analysis request)'
                }

                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    className={cn('flex gap-2', isUser ? 'justify-end' : 'justify-start')}
                  >
                    {!isUser && (
                      <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="h-3 w-3 text-primary" />
                      </div>
                    )}
                    <div className={cn('max-w-[90%]', isUser ? 'order-first' : '')}>
                      <div
                        className={cn(
                          'rounded-xl text-xs',
                          isUser
                            ? 'bg-primary text-primary-foreground px-3 py-2 rounded-tr-sm'
                            : 'bg-card/80 border border-border/40 px-3 py-2 rounded-tl-sm',
                        )}
                      >
                        {isUser ? (
                          <p className="whitespace-pre-wrap leading-relaxed">{displayText}</p>
                        ) : (
                          <div className="text-foreground/90">
                            <Md content={rawText} />
                          </div>
                        )}
                      </div>
                    </div>
                    {isUser && (
                      <div className="w-6 h-6 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
                        <User className="h-3 w-3 text-muted-foreground" />
                      </div>
                    )}
                  </motion.div>
                )
              })}
            </AnimatePresence>

            {/* Streaming indicator */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-2"
              >
                <div className="w-6 h-6 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <Bot className="h-3 w-3 text-primary animate-pulse" />
                </div>
                <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl rounded-tl-sm bg-card/80 border border-border/40">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      className="w-1 h-1 rounded-full bg-primary"
                      animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
                      transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
                    />
                  ))}
                  <span className="text-[10px] text-muted-foreground ml-1">Analyzing…</span>
                </div>
              </motion.div>
            )}

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Scroll-to-bottom */}
      <AnimatePresence>
        {showScrollBtn && hasMessages && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' })}
            className="absolute bottom-16 left-1/2 -translate-x-1/2 z-10 w-6 h-6 rounded-full bg-card border border-border/50 shadow flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowDown className="h-3 w-3" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Input */}
      <div className="px-3 py-2 border-t border-border/50 shrink-0">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={`Ask about ${filename}…`}
            rows={1}
            className="flex-1 rounded-lg border border-border/50 bg-background/50 px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 resize-none min-h-[28px] max-h-[100px]"
          />
          {isLoading ? (
            <button
              type="button"
              onClick={stop}
              className="h-7 w-7 rounded-lg bg-destructive/10 text-destructive flex items-center justify-center hover:bg-destructive/20 transition-colors shrink-0"
            >
              <StopCircle className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              type="submit"
              className="h-7 w-7 rounded-lg bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors shrink-0 disabled:opacity-50"
              disabled={isLoading}
            >
              <Send className="h-3 w-3" />
            </button>
          )}
        </form>
      </div>
    </div>
  )
}
