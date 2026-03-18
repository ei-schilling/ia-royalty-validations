/** ChatTypingIndicator — animated dots shown while streaming an AI response. */

import { motion } from 'motion/react'
import { Bot } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatTypingIndicatorProps {
  variant?: 'compact' | 'full'
  label?: string
}

export function ChatTypingIndicator({
  variant = 'full',
  label = 'Analyzing…',
}: ChatTypingIndicatorProps) {
  const isCompact = variant === 'compact'

  return (
    <motion.div
      initial={{ opacity: 0, y: isCompact ? 8 : 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn('flex', isCompact ? 'gap-2' : 'gap-3 py-1.5')}
    >
      <div
        className={cn(
          'rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center shrink-0',
          isCompact ? 'w-6 h-6 rounded-lg' : 'w-8 h-8 ring-1 ring-primary/10',
        )}
      >
        <motion.div
          animate={isCompact ? {} : { rotate: [0, 10, -10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Bot className={cn('text-primary', isCompact ? 'h-3 w-3 animate-pulse' : 'h-4 w-4')} />
        </motion.div>
      </div>
      <div
        className={cn(
          'flex items-center gap-2 bg-card/80 border border-border/40',
          isCompact
            ? 'gap-1.5 px-3 py-2 rounded-xl rounded-tl-sm'
            : 'px-5 py-3 rounded-2xl rounded-tl-md shadow-sm',
        )}
      >
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className={cn('rounded-full bg-primary', isCompact ? 'w-1 h-1' : 'w-1.5 h-1.5')}
              animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
              transition={{
                duration: isCompact ? 1 : 1.2,
                repeat: Infinity,
                delay: i * 0.15,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
        <span
          className={cn(
            'text-muted-foreground font-medium ml-1',
            isCompact ? 'text-[10px]' : 'text-xs',
          )}
        >
          {label}
        </span>
      </div>
    </motion.div>
  )
}
