/** ChatSuggestionChips — quick reply suggestions shown after assistant responses. */

import { motion } from 'motion/react'
import { Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { ChatSuggestion } from '../types'

interface ChatSuggestionChipsProps {
  suggestions: ChatSuggestion[]
  onSelect: (text: string) => void
  variant?: 'compact' | 'full'
}

export function ChatSuggestionChips({
  suggestions,
  onSelect,
  variant = 'full',
}: ChatSuggestionChipsProps) {
  const isCompact = variant === 'compact'

  if (suggestions.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.4 }}
      className={cn('flex flex-wrap gap-1.5', isCompact ? 'ml-8 mt-1' : 'ml-11 mt-2')}
    >
      <div className="flex items-center gap-1 mr-1">
        <Sparkles className={cn('text-primary/40', isCompact ? 'h-2 w-2' : 'h-2.5 w-2.5')} />
      </div>
      {suggestions.map((s, i) => (
        <motion.button
          key={s.text}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 + i * 0.05 }}
          onClick={() => onSelect(s.text)}
          className={cn(
            'inline-flex items-center gap-1 rounded-full border border-border/50',
            'bg-card/60 text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/5',
            'transition-all cursor-pointer',
            isCompact ? 'px-2 py-0.5 text-[9px]' : 'px-3 py-1 text-[11px]',
          )}
        >
          {s.icon && <span className={isCompact ? 'text-[9px]' : 'text-xs'}>{s.icon}</span>}
          <span>{s.text}</span>
        </motion.button>
      ))}
    </motion.div>
  )
}
