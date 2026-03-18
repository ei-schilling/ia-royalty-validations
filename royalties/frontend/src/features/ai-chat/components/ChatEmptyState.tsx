/** ChatEmptyState — beautiful empty state with suggestions for starting a conversation. */

import { motion } from 'motion/react'
import { Bot, Paperclip } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatSuggestion } from '../types'

interface ChatEmptyStateProps {
  variant?: 'compact' | 'full'
  title?: string
  description?: string
  /** Contextual subtitle (e.g. filename for document chat) */
  contextLabel?: string
  suggestions: ChatSuggestion[]
  onSuggestionClick: (text: string) => void
  showUploadHint?: boolean
}

export function ChatEmptyState({
  variant = 'full',
  title = 'AI Assistant',
  description = 'Ask questions, upload documents, or explore topics.',
  contextLabel,
  suggestions,
  onSuggestionClick,
  showUploadHint = false,
}: ChatEmptyStateProps) {
  const isCompact = variant === 'compact'

  if (isCompact) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-4 py-6">
        <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
          <Bot className="h-5 w-5 text-primary" />
        </div>
        {contextLabel && (
          <p className="text-xs text-muted-foreground text-center mb-4 max-w-[200px]">
            Ask questions about <span className="font-medium text-foreground">{contextLabel}</span>
          </p>
        )}
        <div className="space-y-1.5 w-full">
          {suggestions.map((s) => (
            <button
              key={s.text}
              onClick={() => onSuggestionClick(s.text)}
              className="w-full text-left text-[11px] px-3 py-2 rounded-lg border border-border/40 bg-card/50 hover:bg-card hover:border-primary/30 transition-all text-muted-foreground hover:text-foreground"
            >
              {s.icon && <span className="mr-1.5">{s.icon}</span>}
              {s.text}
            </button>
          ))}
        </div>
      </div>
    )
  }

  return (
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
          {title}
        </motion.h2>
        <motion.p
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="text-sm text-muted-foreground mb-10 leading-relaxed max-w-sm"
        >
          {description}
        </motion.p>

        {/* Suggestion grid */}
        <div
          className={cn(
            'grid gap-2 w-full',
            suggestions.length <= 4
              ? 'grid-cols-1 sm:grid-cols-2'
              : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
          )}
        >
          {suggestions.map((s, i) => (
            <motion.button
              key={s.text}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 + i * 0.06, duration: 0.35 }}
              whileHover={{ scale: 1.02, y: -2 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onSuggestionClick(s.text)}
              className="text-left px-4 py-3.5 rounded-xl border border-border/40 bg-card/50 hover:bg-card hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all text-xs group"
            >
              {s.icon && <span className="text-base mb-1.5 block">{s.icon}</span>}
              <span className="text-muted-foreground group-hover:text-foreground transition-colors leading-snug">
                {s.text}
              </span>
            </motion.button>
          ))}
        </div>

        {/* Upload hint */}
        {showUploadHint && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8, duration: 0.5 }}
            className="mt-8 flex items-center gap-2 text-[11px] text-muted-foreground/50"
          >
            <Paperclip className="h-3 w-3" />
            <span>Drop files or use the attachment button to upload documents</span>
          </motion.div>
        )}
      </motion.div>
    </div>
  )
}
