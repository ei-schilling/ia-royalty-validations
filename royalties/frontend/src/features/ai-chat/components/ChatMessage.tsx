/** ChatMessage — renders a single chat message with avatar, timestamps, status, and actions. */

import { motion } from 'motion/react'
import { Bot, User, Clock, AlertCircle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ChatMarkdown } from './ChatMarkdown'
import { ChatMessageActions } from './ChatMessageActions'
import type { MessageStatus } from '../types'

/* ─── Helpers ─────────────────────────────────────────── */
function formatTime(ts?: string | number): string | null {
  if (!ts) return null
  const d = typeof ts === 'number' ? new Date(ts) : new Date(ts)
  if (isNaN(d.getTime())) return null
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/** Inline blinking cursor shown at the end of streaming content */
function StreamingCursor({ compact }: { compact?: boolean }) {
  return (
    <motion.span
      className={cn(
        'inline-block bg-primary rounded-[1px] translate-y-[1px]',
        compact ? 'w-[2px] h-[14px] ml-0.5' : 'w-[2px] h-[16px] ml-0.5',
      )}
      animate={{ opacity: [1, 0] }}
      transition={{ duration: 0.6, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}

/* ─── Props ───────────────────────────────────────────── */
interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  variant?: 'compact' | 'full'
  /** Whether this is the last assistant message (enables actions) */
  isLatest?: boolean
  /** Delay for entrance animation */
  animationDelay?: number
  /** Timestamp for the message */
  createdAt?: string | number
  /** Delivery / streaming status */
  status?: MessageStatus
  /** Error details */
  error?: string
  /** Callback to retry a failed or regenerate the last message */
  onRetry?: () => void
}

export function ChatMessage({
  role,
  content,
  variant = 'full',
  isLatest = false,
  animationDelay = 0,
  createdAt,
  status,
  error,
  onRetry,
}: ChatMessageProps) {
  const isUser = role === 'user'
  const isCompact = variant === 'compact'
  const isError = status === 'error'
  const timeStr = formatTime(createdAt)

  return (
    <motion.div
      initial={{ opacity: 0, y: isCompact ? 8 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: isCompact ? 0.25 : 0.35,
        ease: [0.22, 1, 0.36, 1],
        delay: animationDelay,
      }}
      className={cn(
        'group/msg flex',
        isCompact ? 'gap-2' : 'gap-3',
        isUser ? 'justify-end' : 'justify-start',
        isCompact ? '' : 'py-1.5',
      )}
    >
      {/* Assistant avatar */}
      {!isUser && (
        <motion.div
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 300, delay: 0.05 }}
          className={cn(
            'rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center shrink-0 mt-0.5',
            isCompact ? 'w-6 h-6 rounded-lg ring-0' : 'w-8 h-8 ring-1 ring-primary/10',
          )}
        >
          <Bot className={cn('text-primary', isCompact ? 'h-3 w-3' : 'h-4 w-4')} />
        </motion.div>
      )}

      {/* Bubble + meta */}
      <div
        className={cn(
          isUser ? 'order-first' : '',
          isCompact ? 'max-w-[90%]' : 'max-w-[85%] md:max-w-[75%]',
        )}
      >
        <div
          className={cn(
            'rounded-2xl',
            isCompact ? 'text-xs' : 'text-sm',
            isError && 'ring-1 ring-destructive/30',
            isUser
              ? cn(
                  'bg-primary text-primary-foreground',
                  isCompact ? 'px-3 py-2 rounded-tr-sm' : 'px-4 py-3 rounded-tr-md',
                )
              : cn(
                  'bg-card/80 border border-border/40',
                  isCompact ? 'px-3 py-2 rounded-tl-sm' : 'px-5 py-4 rounded-tl-md shadow-sm',
                ),
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
          ) : (
            <div className="text-foreground/90">
              <ChatMarkdown content={content} variant={variant} />
              {status === 'streaming' && <StreamingCursor compact={isCompact} />}
            </div>
          )}

          {/* Error banner inside bubble */}
          {isError && error && (
            <div className="mt-2 flex items-center gap-2 text-destructive text-[11px]">
              <AlertCircle className="h-3 w-3 shrink-0" />
              <span className="line-clamp-2">{error}</span>
            </div>
          )}
        </div>

        {/* Meta row: time, status, actions */}
        <div
          className={cn(
            'flex items-center mt-1 gap-2',
            isUser ? 'justify-end' : 'justify-start',
            isCompact ? 'mx-1' : 'mx-1.5',
          )}
        >
          {/* Timestamp — visible on hover for compact, always for full with opacity transition */}
          {timeStr && (
            <span
              className={cn(
                'flex items-center gap-1 text-muted-foreground/40 transition-opacity',
                isCompact
                  ? 'text-[9px] opacity-0 group-hover/msg:opacity-100'
                  : 'text-[10px] opacity-60 group-hover/msg:opacity-100',
              )}
            >
              <Clock className="h-2.5 w-2.5" />
              {timeStr}
            </span>
          )}

          {/* Error indicator in meta row (streaming handled by inline cursor) */}
          {status === 'error' && <AlertCircle className="h-2.5 w-2.5 text-destructive" />}

          {/* Retry button for errors */}
          {isError && onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1 text-[10px] text-destructive hover:text-destructive/80 transition-colors"
            >
              <RefreshCw className="h-2.5 w-2.5" />
              <span>Retry</span>
            </button>
          )}

          {/* Actions for latest assistant message */}
          {!isUser && isLatest && !isCompact && !isError && (
            <ChatMessageActions content={content} onRetry={onRetry} />
          )}
        </div>
      </div>

      {/* User avatar */}
      {isUser && (
        <motion.div
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 300, delay: 0.05 }}
          className={cn(
            'rounded-xl bg-muted flex items-center justify-center shrink-0 mt-0.5',
            isCompact ? 'w-6 h-6 rounded-lg' : 'w-8 h-8 ring-1 ring-border/50',
          )}
        >
          <User className={cn('text-muted-foreground', isCompact ? 'h-3 w-3' : 'h-4 w-4')} />
        </motion.div>
      )}
    </motion.div>
  )
}
