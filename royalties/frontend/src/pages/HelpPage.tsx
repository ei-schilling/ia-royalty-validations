/** Help page — premium AI chat assistant with markdown + file upload. */

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useMemo,
  type FormEvent,
  type DragEvent,
} from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Send,
  Bot,
  User,
  Sparkles,
  Eraser,
  StopCircle,
  Paperclip,
  X,
  FileText,
  FileSpreadsheet,
  FileJson,
  FileType2,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  ArrowDown,
  Database,
  Search,
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useChat, fetchServerSentEvents } from '@tanstack/ai-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

/* ─── File type helpers ──────────────────────────────── */
const FILE_ICONS: Record<string, typeof FileText> = {
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  json: FileJson,
  pdf: FileType2,
  txt: FileText,
  md: FileText,
  doc: FileText,
  docx: FileText,
}
const FILE_COLORS: Record<string, string> = {
  csv: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  xlsx: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  xls: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  json: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  pdf: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  txt: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  md: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  doc: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  docx: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
}

function getFileInfo(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const Icon = FILE_ICONS[ext] || FileText
  const color = FILE_COLORS[ext] || 'text-muted-foreground bg-muted/50 border-border/50'
  return { ext, Icon, color }
}

/* ─── Copy button for code blocks ────────────────────── */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }}
      className="absolute top-2 right-2 p-1.5 rounded-md bg-background/80 border border-border/50 text-muted-foreground hover:text-foreground hover:bg-muted transition-all opacity-0 group-hover/pre:opacity-100"
    >
      {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
    </button>
  )
}

/* ─── Markdown renderer ──────────────────────────────── */
function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-3 last:mb-0 leading-relaxed">{children}</p>,
        h1: ({ children }) => (
          <h1 className="text-lg font-display font-bold mb-3 mt-4 first:mt-0 text-foreground">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-display font-semibold mb-2 mt-3 first:mt-0 text-foreground">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-display font-semibold mb-2 mt-3 first:mt-0 text-foreground">
            {children}
          </h3>
        ),
        ul: ({ children }) => (
          <ul className="mb-3 ml-4 space-y-1 list-disc marker:text-primary/50">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-3 ml-4 space-y-1 list-decimal marker:text-primary/50">{children}</ol>
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
          <blockquote className="border-l-2 border-primary/30 pl-4 my-3 text-muted-foreground italic">
            {children}
          </blockquote>
        ),
        code: ({ className, children }) => {
          const isBlock = className?.includes('language-')
          if (isBlock) {
            const text = String(children).replace(/\n$/, '')
            return (
              <div className="group/pre relative my-3">
                <pre className="overflow-x-auto rounded-lg bg-background/80 border border-border/50 p-4 text-xs font-mono leading-relaxed">
                  <code className={className}>{children}</code>
                </pre>
                <CopyButton text={text} />
              </div>
            )
          }
          return (
            <code className="px-1.5 py-0.5 rounded-md bg-primary/10 text-primary text-[0.85em] font-mono">
              {children}
            </code>
          )
        },
        pre: ({ children }) => <>{children}</>,
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto rounded-lg border border-border/50">
            <table className="w-full text-xs">{children}</table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className="bg-muted/50 border-b border-border/50">{children}</thead>
        ),
        th: ({ children }) => (
          <th className="px-3 py-2 text-left font-semibold text-foreground">{children}</th>
        ),
        td: ({ children }) => (
          <td className="px-3 py-2 border-t border-border/30 text-muted-foreground">{children}</td>
        ),
        hr: () => <hr className="my-4 border-border/30" />,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

/* ─── Suggestions ────────────────────────────────────── */
const SUGGESTIONS = [
  { icon: '📊', text: 'What are common royalty rate structures?' },
  { icon: '✅', text: 'How do I validate royalty amounts?' },
  { icon: '🔄', text: 'Explain the settlement reconciliation process' },
  { icon: '⚠️', text: 'What causes duplicate entries in statements?' },
  { icon: '📋', text: 'Summarize best practices for royalty reporting' },
  { icon: '🔍', text: 'What validation rules does this system check?' },
]

/* ─── Attached file chip ─────────────────────────────── */
function FileChip({
  file,
  status,
  onRemove,
}: {
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
  onRemove?: () => void
}) {
  const { ext, Icon, color } = getFileInfo(file.name)
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.8, y: -10 }}
      className={cn('inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs', color)}
    >
      <Icon className="h-3.5 w-3.5 shrink-0" />
      <span className="max-w-[140px] truncate font-medium">{file.name}</span>
      <span className="uppercase opacity-60">.{ext}</span>
      {status === 'uploading' && (
        <motion.div
          className="h-3 w-3 rounded-full border-2 border-current border-t-transparent"
          animate={{ rotate: 360 }}
          transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
        />
      )}
      {status === 'done' && <CheckCircle2 className="h-3 w-3 text-emerald-400" />}
      {status === 'error' && <AlertCircle className="h-3 w-3 text-destructive" />}
      {onRemove && status === 'pending' && (
        <button onClick={onRemove} className="ml-1 hover:text-foreground transition-colors">
          <X className="h-3 w-3" />
        </button>
      )}
    </motion.div>
  )
}

/* ─── Main component ─────────────────────────────────── */
export default function HelpPage() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [attachedFiles, setAttachedFiles] = useState<File[]>([])
  const [uploadStates, setUploadStates] = useState<
    Record<string, 'pending' | 'uploading' | 'done' | 'error'>
  >({})
  const [uploadedDocs, setUploadedDocs] = useState<
    { name: string; contentFull?: string; type?: string }[]
  >([])
  const [isDragging, setIsDragging] = useState(false)
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const [chatMode, setChatMode] = useState<'query' | 'agent'>('query')

  const connection = useMemo(
    () => fetchServerSentEvents(`/api/chat/stream?mode=${chatMode}`),
    [chatMode],
  )

  const { messages, sendMessage, isLoading, stop, clear } = useChat({
    connection,
  })

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  // Show/hide scroll-to-bottom button
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
    setShowScrollBtn(!atBottom)
  }, [])

  function scrollToBottom() {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  /* ── File upload logic ── */
  async function uploadFile(
    file: File,
  ): Promise<{ name: string; contentFull?: string; type?: string } | null> {
    const key = file.name + file.size
    setUploadStates((s) => ({ ...s, [key]: 'uploading' }))
    try {
      const fd = new FormData()
      fd.append('file', file)
      const resp = await fetch('/api/chat/upload', { method: 'POST', body: fd })
      const data = await resp.json()
      if (data.success) {
        setUploadStates((s) => ({ ...s, [key]: 'done' }))
        const doc = {
          name: file.name,
          contentFull: data.document?.contentFull as string | undefined,
          type: data.document?.type as string | undefined,
        }
        setUploadedDocs((prev) => [...prev, doc])
        return doc
      }
      setUploadStates((s) => ({ ...s, [key]: 'error' }))
      return null
    } catch {
      setUploadStates((s) => ({ ...s, [key]: 'error' }))
      return null
    }
  }

  function addFiles(files: FileList | File[]) {
    const newFiles = Array.from(files)
    setAttachedFiles((prev) => [...prev, ...newFiles])
    newFiles.forEach((f) => {
      setUploadStates((s) => ({ ...s, [f.name + f.size]: 'pending' }))
    })
  }

  function removeFile(index: number) {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  /* ── Drag & drop ── */
  function handleDragOver(e: DragEvent) {
    e.preventDefault()
    setIsDragging(true)
  }
  function handleDragLeave(e: DragEvent) {
    e.preventDefault()
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDragging(false)
  }
  function handleDrop(e: DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
  }

  /* ── Submit ── */
  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const value = inputRef.current?.value.trim()
    if ((!value && attachedFiles.length === 0) || isLoading) return

    // Upload pending files and collect results directly (don't rely on React state timing)
    const pending = attachedFiles.filter((f) => uploadStates[f.name + f.size] === 'pending')
    let freshDocs: { name: string; contentFull?: string; type?: string }[] = []
    if (pending.length > 0) {
      const results = await Promise.all(pending.map(uploadFile))
      freshDocs = results.filter(Boolean) as typeof freshDocs
    }

    // Combine with any previously uploaded docs in this batch
    const allDocs = [
      ...uploadedDocs.filter((d) => !freshDocs.some((f) => f.name === d.name)),
      ...freshDocs,
    ]

    // Build message: inject full document text so the LLM can actually read the content
    let messageText = value || ''

    if (allDocs.length > 0) {
      const docBlocks = allDocs
        .filter((d) => d.contentFull)
        .map((d) => `--- Document: ${d.name} ---\n${d.contentFull}\n--- End of ${d.name} ---`)

      if (docBlocks.length > 0) {
        const instruction =
          messageText ||
          `Please analyze ${allDocs.length > 1 ? 'these documents' : 'this document'} and provide a detailed summary.`
        messageText = `${instruction}\n\n${docBlocks.join('\n\n')}`
      } else if (!messageText) {
        const names = allDocs.map((d) => `"${d.name}"`).join(', ')
        messageText = `I've uploaded ${names}. Please analyze ${allDocs.length > 1 ? 'these documents' : 'this document'} and provide a summary.`
      }
    }

    if (messageText) {
      sendMessage(messageText)
    }
    if (inputRef.current) inputRef.current.value = ''
    setAttachedFiles([])
    setUploadStates({})
    setUploadedDocs([])
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Auto-resize textarea
  function handleInput() {
    if (!inputRef.current) return
    inputRef.current.style.height = 'auto'
    inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 160) + 'px'
  }

  const hasMessages = messages.length > 0

  return (
    <TooltipProvider>
      <div
        className="flex flex-col h-[calc(100vh-10rem)] relative"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Drag overlay */}
        <AnimatePresence>
          {isDragging && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-50 flex items-center justify-center rounded-2xl border-2 border-dashed border-primary/50 bg-primary/5 backdrop-blur-sm"
            >
              <div className="flex flex-col items-center gap-3">
                <motion.div
                  animate={{ y: [0, -8, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center"
                >
                  <Paperclip className="h-7 w-7 text-primary" />
                </motion.div>
                <p className="text-sm font-medium text-foreground">Drop files here</p>
                <p className="text-xs text-muted-foreground">
                  CSV, XLSX, JSON, PDF, TXT, MD, images
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Chat area ── */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto scroll-smooth"
        >
          {!hasMessages ? (
            /* ── Empty state ── */
            <div className="flex flex-col items-center justify-center h-full px-6">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
                className="flex flex-col items-center text-center max-w-lg"
              >
                {/* Animated logo */}
                <motion.div
                  initial={{ scale: 0.5, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ duration: 0.5, delay: 0.1, type: 'spring', stiffness: 200 }}
                  className="relative mb-8"
                >
                  <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                    <Bot className="h-9 w-9 text-primary" />
                  </div>
                  {/* Orbiting dots */}
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                    className="absolute inset-0"
                  >
                    <div className="absolute -top-1 left-1/2 w-2 h-2 -translate-x-1/2 rounded-full bg-primary/40" />
                  </motion.div>
                  <motion.div
                    animate={{ rotate: -360 }}
                    transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
                    className="absolute -inset-2"
                  >
                    <div className="absolute top-0 right-0 w-1.5 h-1.5 rounded-full bg-primary/20" />
                  </motion.div>
                  {/* Glow */}
                  <div className="absolute inset-0 rounded-3xl glow-primary opacity-50" />
                </motion.div>

                <motion.h2
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.4 }}
                  className="font-display text-2xl font-bold text-foreground mb-2"
                >
                  Royalty Assistant
                </motion.h2>
                <motion.p
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3, duration: 0.4 }}
                  className="text-sm text-muted-foreground mb-10 leading-relaxed max-w-sm"
                >
                  Ask about royalty settlements, upload documents for analysis, or get help with
                  validation rules.
                </motion.p>

                {/* Suggestion grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 w-full">
                  {SUGGESTIONS.map((s, i) => (
                    <motion.button
                      key={s.text}
                      initial={{ opacity: 0, y: 15 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.35 + i * 0.06, duration: 0.35 }}
                      whileHover={{ scale: 1.02, y: -2 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => sendMessage(s.text)}
                      className="text-left px-4 py-3.5 rounded-xl border border-border/40 bg-card/50 hover:bg-card hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all text-xs group"
                    >
                      <span className="text-base mb-1.5 block">{s.icon}</span>
                      <span className="text-muted-foreground group-hover:text-foreground transition-colors leading-snug">
                        {s.text}
                      </span>
                    </motion.button>
                  ))}
                </div>

                {/* Upload hint */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.8, duration: 0.5 }}
                  className="mt-8 flex items-center gap-2 text-[11px] text-muted-foreground/50"
                >
                  <Paperclip className="h-3 w-3" />
                  <span>Drop files or use the attachment button to upload documents</span>
                </motion.div>
              </motion.div>
            </div>
          ) : (
            /* ── Messages ── */
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-1">
              <AnimatePresence initial={false}>
                {messages.map((msg, idx) => {
                  const isUser = msg.role === 'user'
                  const textParts = msg.parts?.filter((p: { type: string }) => p.type === 'text')
                  const rawText =
                    textParts
                      ?.map((p: { type: string; content?: string }) => p.content || '')
                      .join('') || ''

                  if (!rawText) return null

                  // For user messages, strip inline document dumps and show a clean version
                  let displayText = rawText
                  if (isUser && rawText.includes('--- Document:')) {
                    const docPattern = /\n?\n?--- Document: (.+?) ---[\s\S]*?--- End of \1 ---/g
                    const docNames: string[] = []
                    let match: RegExpExecArray | null
                    while ((match = docPattern.exec(rawText)) !== null) {
                      docNames.push(match[1])
                    }
                    displayText = rawText
                      .replace(/\n?\n?--- Document: .+? ---[\s\S]*?--- End of .+? ---/g, '')
                      .trim()
                    if (docNames.length > 0) {
                      const label = docNames.map((n) => `📎 ${n}`).join('\n')
                      displayText = displayText ? `${displayText}\n\n${label}` : label
                    }
                  }

                  return (
                    <motion.div
                      key={msg.id}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{
                        duration: 0.35,
                        ease: [0.22, 1, 0.36, 1],
                        delay: idx === messages.length - 1 ? 0.05 : 0,
                      }}
                      className={cn('flex gap-3 py-3', isUser ? 'justify-end' : 'justify-start')}
                    >
                      {/* Assistant avatar */}
                      {!isUser && (
                        <motion.div
                          initial={{ scale: 0.5, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          transition={{ type: 'spring', stiffness: 300, delay: 0.05 }}
                          className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center shrink-0 mt-0.5 ring-1 ring-primary/10"
                        >
                          <Bot className="h-4 w-4 text-primary" />
                        </motion.div>
                      )}

                      {/* Bubble */}
                      <div
                        className={cn('max-w-[85%] md:max-w-[75%]', isUser ? 'order-first' : '')}
                      >
                        <div
                          className={cn(
                            'rounded-2xl text-sm',
                            isUser
                              ? 'bg-primary text-primary-foreground px-4 py-3 rounded-tr-md'
                              : 'bg-card/80 border border-border/40 px-5 py-4 rounded-tl-md shadow-sm',
                          )}
                        >
                          {isUser ? (
                            <p className="whitespace-pre-wrap leading-relaxed">{displayText}</p>
                          ) : (
                            <div className="text-foreground/90">
                              <MarkdownContent content={rawText} />
                            </div>
                          )}
                        </div>
                      </div>

                      {/* User avatar */}
                      {isUser && (
                        <motion.div
                          initial={{ scale: 0.5, opacity: 0 }}
                          animate={{ scale: 1, opacity: 1 }}
                          transition={{ type: 'spring', stiffness: 300, delay: 0.05 }}
                          className="w-8 h-8 rounded-xl bg-muted flex items-center justify-center shrink-0 mt-0.5 ring-1 ring-border/50"
                        >
                          <User className="h-4 w-4 text-muted-foreground" />
                        </motion.div>
                      )}
                    </motion.div>
                  )
                })}
              </AnimatePresence>

              {/* Streaming indicator */}
              {isLoading && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3 py-3"
                >
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center shrink-0 ring-1 ring-primary/10">
                    <motion.div
                      animate={{ rotate: [0, 10, -10, 0] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      <Bot className="h-4 w-4 text-primary" />
                    </motion.div>
                  </div>
                  <div className="flex items-center gap-2 px-5 py-3 rounded-2xl rounded-tl-md bg-card/80 border border-border/40 shadow-sm">
                    <div className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <motion.div
                          key={i}
                          className="w-1.5 h-1.5 rounded-full bg-primary"
                          animate={{
                            scale: [1, 1.4, 1],
                            opacity: [0.4, 1, 0.4],
                          }}
                          transition={{
                            duration: 1.2,
                            repeat: Infinity,
                            delay: i * 0.15,
                            ease: 'easeInOut',
                          }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-muted-foreground font-medium ml-1">
                      Analyzing…
                    </span>
                  </div>
                </motion.div>
              )}

              <div ref={bottomRef} />
            </div>
          )}
        </div>

        {/* Scroll-to-bottom fab */}
        <AnimatePresence>
          {showScrollBtn && hasMessages && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={scrollToBottom}
              className="absolute bottom-32 left-1/2 -translate-x-1/2 z-30 w-8 h-8 rounded-full bg-card border border-border/50 shadow-lg flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowDown className="h-3.5 w-3.5" />
            </motion.button>
          )}
        </AnimatePresence>

        {/* ── Input area ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.4 }}
          className="mt-3 relative"
        >
          {/* Uploaded file badges (above input for context) */}
          <AnimatePresence>
            {uploadedDocs.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex flex-wrap gap-1.5 mb-2"
              >
                {uploadedDocs.map((doc) => (
                  <Badge key={doc.name} variant="secondary" className="text-[10px] gap-1 pr-1">
                    <CheckCircle2 className="h-2.5 w-2.5 text-emerald-400" />
                    {doc.name}
                    <button
                      onClick={() =>
                        setUploadedDocs((prev) => prev.filter((d) => d.name !== doc.name))
                      }
                      className="ml-0.5 hover:text-foreground"
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  </Badge>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Attached files (pre-upload) */}
          <AnimatePresence>
            {attachedFiles.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex flex-wrap gap-2 mb-2"
              >
                {attachedFiles.map((file, i) => (
                  <FileChip
                    key={file.name + file.size}
                    file={file}
                    status={uploadStates[file.name + file.size] || 'pending'}
                    onRemove={() => removeFile(i)}
                  />
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Input bar */}
          <form onSubmit={handleSubmit} className="relative">
            <div className="flex items-end gap-2 rounded-2xl border border-border/50 bg-card/60 backdrop-blur-sm shadow-sm focus-within:border-primary/40 focus-within:shadow-md focus-within:shadow-primary/5 transition-all">
              {/* Attach button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-3 pb-3.5 text-muted-foreground/60 hover:text-primary transition-colors shrink-0"
                  >
                    <Paperclip className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Attach a file</TooltipContent>
              </Tooltip>

              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".csv,.xlsx,.xls,.json,.pdf,.txt,.md,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp,.bmp,.svg"
                multiple
                onChange={(e) => e.target.files && addFiles(e.target.files)}
              />

              <textarea
                ref={inputRef}
                placeholder="Ask something or drop a file…"
                rows={1}
                onKeyDown={handleKeyDown}
                onInput={handleInput}
                className="flex-1 resize-none bg-transparent py-3.5 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none min-h-[44px] max-h-[160px] leading-relaxed"
              />

              {/* Action buttons */}
              <div className="flex items-center gap-1 pr-2 pb-2.5">
                {/* Mode toggle: RAG ↔ Agent (SQL) */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => setChatMode((m) => (m === 'query' ? 'agent' : 'query'))}
                      className={cn(
                        'p-1.5 rounded-lg transition-all flex items-center gap-1',
                        chatMode === 'agent'
                          ? 'text-primary bg-primary/10 ring-1 ring-primary/30'
                          : 'text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50',
                      )}
                    >
                      {chatMode === 'agent' ? (
                        <Database className="h-3.5 w-3.5" />
                      ) : (
                        <Search className="h-3.5 w-3.5" />
                      )}
                      <span className="text-[10px] font-medium uppercase tracking-wider pr-0.5">
                        {chatMode === 'agent' ? 'SQL' : 'RAG'}
                      </span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {chatMode === 'agent'
                      ? 'Agent mode: can query the database'
                      : 'RAG mode: searches documents'}
                  </TooltipContent>
                </Tooltip>

                {hasMessages && !isLoading && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={() => {
                          clear()
                          setUploadedDocs([])
                        }}
                        className="p-1.5 rounded-lg text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50 transition-all"
                      >
                        <Eraser className="h-3.5 w-3.5" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Clear chat</TooltipContent>
                  </Tooltip>
                )}

                {isLoading ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        onClick={stop}
                        className="p-2 rounded-xl bg-destructive/10 text-destructive hover:bg-destructive/20 transition-all"
                      >
                        <StopCircle className="h-4 w-4" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Stop</TooltipContent>
                  </Tooltip>
                ) : (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="submit"
                        className="p-2 rounded-xl bg-primary text-primary-foreground hover:brightness-110 transition-all shadow-sm"
                      >
                        <Send className="h-4 w-4" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>Send message</TooltipContent>
                  </Tooltip>
                )}
              </div>
            </div>
          </form>

          {/* Footer */}
          <div className="flex items-center justify-center gap-2 mt-2.5">
            <Sparkles className="h-3 w-3 text-muted-foreground/30" />
            <span className="text-[10px] text-muted-foreground/30 tracking-wide">
              Powered by your royalty knowledge base
            </span>
          </div>
        </motion.div>
      </div>
    </TooltipProvider>
  )
}
