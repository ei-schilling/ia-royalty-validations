/** Help page — AI chat assistant for royalty settlement questions. */

import { useRef, useEffect, type FormEvent } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Send,
  Bot,
  User,
  Sparkles,
  MessageSquare,
  Eraser,
  StopCircle,
  BookOpenCheck,
} from 'lucide-react'
import { useChat, fetchServerSentEvents } from '@tanstack/ai-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const SUGGESTIONS = [
  'What are the common royalty rate structures?',
  'How do I validate royalty amounts?',
  'Explain the settlement reconciliation process',
  'What causes duplicate entries in statements?',
]

export default function HelpPage() {
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const { messages, sendMessage, isLoading, stop, clear } = useChat({
    connection: fetchServerSentEvents('/api/chat/stream'),
  })

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const value = inputRef.current?.value.trim()
    if (!value || isLoading) return
    sendMessage(value)
    if (inputRef.current) inputRef.current.value = ''
  }

  function handleSuggestion(text: string) {
    sendMessage(text)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const hasMessages = messages.length > 0

  return (
    <div className="flex flex-col h-[calc(100vh-10rem)]">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-4"
      >
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10">
            <Bot className="w-5 h-5 text-primary" />
            <div className="absolute inset-0 rounded-xl ring-1 ring-primary/20" />
          </div>
          <div>
            <h1 className="text-lg font-semibold leading-none font-display text-foreground">
              Royalty Assistant
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              AI-powered help for royalty settlements
            </p>
          </div>
        </div>
        {hasMessages && (
          <Button
            variant="ghost"
            size="sm"
            onClick={clear}
            className="gap-1.5 text-muted-foreground hover:text-foreground"
          >
            <Eraser className="h-3.5 w-3.5" />
            Clear
          </Button>
        )}
      </motion.div>

      {/* Chat area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto border rounded-xl border-border/50 bg-background/50 backdrop-blur-sm"
      >
        {!hasMessages ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full px-6 py-12">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              className="flex flex-col items-center max-w-md text-center"
            >
              <div className="flex items-center justify-center w-16 h-16 mb-6 rounded-2xl bg-primary/10">
                <BookOpenCheck className="w-8 h-8 text-primary" />
              </div>
              <h2 className="mb-2 text-xl font-semibold font-display text-foreground">
                How can I help?
              </h2>
              <p className="mb-8 text-sm leading-relaxed text-muted-foreground">
                Ask me anything about royalty statements, settlement processes, validation rules, or
                common issues.
              </p>
              <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSuggestion(s)}
                    className="px-4 py-3 text-xs text-left transition-all border rounded-lg border-border/50 bg-muted/30 hover:bg-muted/60 hover:border-primary/30 text-muted-foreground hover:text-foreground group"
                  >
                    <div className="flex items-start gap-2">
                      <Sparkles className="h-3.5 w-3.5 text-primary/50 group-hover:text-primary mt-0.5 shrink-0" />
                      <span>{s}</span>
                    </div>
                  </button>
                ))}
              </div>
            </motion.div>
          </div>
        ) : (
          /* Messages */
          <div className="p-4 space-y-4">
            <AnimatePresence initial={false}>
              {messages.map((msg) => {
                const isUser = msg.role === 'user'
                const textParts = msg.parts?.filter((p: { type: string }) => p.type === 'text')
                const text =
                  textParts
                    ?.map((p: { type: string; content?: string }) => p.content || '')
                    .join('') || ''

                if (!text) return null

                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className={cn('flex gap-3', isUser ? 'justify-end' : 'justify-start')}
                  >
                    {!isUser && (
                      <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                        <Bot className="h-3.5 w-3.5 text-primary" />
                      </div>
                    )}
                    <div
                      className={cn(
                        'rounded-xl px-4 py-3 max-w-[80%] text-sm leading-relaxed',
                        isUser
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted/50 border border-border/50 text-foreground',
                      )}
                    >
                      {isUser ? (
                        <p className="whitespace-pre-wrap">{text}</p>
                      ) : (
                        <div className="prose prose-sm prose-invert max-w-none [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:mb-2 [&_li]:mb-0.5 [&_code]:bg-background/50 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_pre]:bg-background/50 [&_pre]:rounded-lg [&_pre]:p-3 whitespace-pre-wrap">
                          {text}
                        </div>
                      )}
                    </div>
                    {isUser && (
                      <div className="w-7 h-7 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
                        <User className="h-3.5 w-3.5 text-muted-foreground" />
                      </div>
                    )}
                  </motion.div>
                )
              })}
            </AnimatePresence>

            {/* Loading indicator */}
            {isLoading && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                <div className="flex items-center justify-center rounded-lg w-7 h-7 bg-primary/10 shrink-0">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="flex items-center gap-1.5 px-4 py-3 rounded-xl bg-muted/50 border border-border/50">
                  <div className="flex gap-1">
                    {[0, 1, 2].map((i) => (
                      <motion.div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-primary/50"
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{
                          duration: 1,
                          repeat: Infinity,
                          delay: i * 0.2,
                        }}
                      />
                    ))}
                  </div>
                  <span className="ml-1 text-xs text-muted-foreground">Thinking…</span>
                </div>
              </motion.div>
            )}
          </div>
        )}
      </div>

      {/* Input area */}
      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        onSubmit={handleSubmit}
        className="flex items-end gap-2 mt-3"
      >
        <div className="relative flex-1">
          <textarea
            ref={inputRef}
            placeholder="Ask about royalty settlements…"
            rows={1}
            onKeyDown={handleKeyDown}
            className="w-full px-4 py-3 pr-12 text-sm transition-all border resize-none rounded-xl border-border/50 bg-muted/30 text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary/50"
          />
          <div className="absolute right-2 bottom-2">
            {isLoading ? (
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                onClick={stop}
                className="text-destructive hover:text-destructive"
              >
                <StopCircle className="w-4 h-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                variant="ghost"
                size="icon-sm"
                className="text-primary hover:text-primary"
              >
                <Send className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </motion.form>

      {/* Footer hint */}
      <div className="flex items-center justify-center gap-1.5 mt-2">
        <MessageSquare className="w-3 h-3 text-muted-foreground/40" />
        <span className="text-[10px] text-muted-foreground/40">
          Powered by your royalty knowledge base · Responses may vary
        </span>
      </div>
    </div>
  )
}
