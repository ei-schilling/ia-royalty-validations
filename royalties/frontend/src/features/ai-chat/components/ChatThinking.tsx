/** ChatThinking — collapsible reasoning/thinking block shown when the AI shares its thought process. */

import { useState } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Brain, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatThinkingProps {
  content: string
  variant?: 'compact' | 'full'
  /** Whether the thinking is still in progress */
  isStreaming?: boolean
  /** Default collapsed state */
  defaultOpen?: boolean
}

export function ChatThinking({
  content,
  variant = 'full',
  isStreaming = false,
  defaultOpen = false,
}: ChatThinkingProps) {
  const [open, setOpen] = useState(defaultOpen)
  const isCompact = variant === 'compact'

  const lines = content.split('\n').filter(Boolean)
  const previewLine = lines[0]?.slice(0, 80) || 'Reasoning…'

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className={cn('overflow-hidden', isCompact ? 'my-1.5' : 'my-2')}
    >
      <div
        className={cn(
          'rounded-xl border border-dashed',
          isStreaming ? 'border-primary/30 bg-primary/[0.03]' : 'border-border/40 bg-muted/20',
        )}
      >
        {/* Header — always visible, toggles collapse */}
        <button
          onClick={() => setOpen(!open)}
          className={cn(
            'w-full flex items-center gap-2 text-left transition-colors hover:bg-muted/30',
            isCompact ? 'px-2.5 py-1.5' : 'px-3.5 py-2',
          )}
        >
          <div className="relative shrink-0">
            <Brain
              className={cn(
                isCompact ? 'h-3 w-3' : 'h-3.5 w-3.5',
                isStreaming ? 'text-primary' : 'text-muted-foreground/60',
              )}
            />
            {isStreaming && (
              <motion.div
                className="absolute -inset-1 rounded-full border border-primary/40"
                animate={{ scale: [1, 1.4, 1], opacity: [0.6, 0, 0.6] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            )}
          </div>

          <span
            className={cn(
              'flex-1 truncate font-medium',
              isCompact ? 'text-[10px]' : 'text-[11px]',
              isStreaming ? 'text-primary/80' : 'text-muted-foreground/60',
            )}
          >
            {isStreaming ? 'Thinking…' : 'Thought process'}
          </span>

          {!isStreaming && (
            <span
              className={cn(
                'truncate max-w-[40%] text-muted-foreground/40',
                isCompact ? 'text-[9px]' : 'text-[10px]',
              )}
            >
              {!open && previewLine}
            </span>
          )}

          <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.2 }}>
            <ChevronDown
              className={cn(
                'shrink-0',
                isCompact ? 'h-2.5 w-2.5' : 'h-3 w-3',
                'text-muted-foreground/40',
              )}
            />
          </motion.div>
        </button>

        {/* Content — collapsible */}
        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div
                className={cn(
                  'border-t border-dashed text-muted-foreground/70 leading-relaxed whitespace-pre-wrap font-mono',
                  isStreaming && 'border-primary/20',
                  isCompact
                    ? 'border-border/30 px-2.5 py-2 text-[9px] max-h-[120px]'
                    : 'border-border/30 px-3.5 py-3 text-[11px] max-h-[200px]',
                  'overflow-y-auto',
                )}
              >
                {content}
                {isStreaming && (
                  <motion.span
                    className="inline-block w-1.5 h-3 bg-primary/60 ml-0.5 rounded-sm"
                    animate={{ opacity: [1, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity }}
                  />
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}
