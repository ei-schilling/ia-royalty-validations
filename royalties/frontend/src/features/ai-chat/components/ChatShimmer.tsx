/** ChatShimmer — skeleton loading state shown while waiting for the first token. */

import { motion } from 'motion/react'
import { Bot } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatShimmerProps {
  variant?: 'compact' | 'full'
}

export function ChatShimmer({ variant = 'full' }: ChatShimmerProps) {
  const isCompact = variant === 'compact'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.3 }}
      className={cn('flex', isCompact ? 'gap-2' : 'gap-3 py-1.5')}
    >
      {/* Avatar */}
      <div
        className={cn(
          'rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center shrink-0 mt-0.5',
          isCompact ? 'w-6 h-6 rounded-lg' : 'w-8 h-8 ring-1 ring-primary/10',
        )}
      >
        <motion.div
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <Bot className={cn('text-primary', isCompact ? 'h-3 w-3' : 'h-4 w-4')} />
        </motion.div>
      </div>

      {/* Shimmer lines */}
      <div
        className={cn(
          'flex-1 space-y-2 bg-card/80 border border-border/40',
          isCompact
            ? 'px-3 py-3 rounded-xl rounded-tl-sm max-w-[85%]'
            : 'px-5 py-4 rounded-2xl rounded-tl-md shadow-sm max-w-[75%]',
        )}
      >
        {[100, 85, 60].map((w, i) => (
          <motion.div
            key={i}
            className={cn('rounded-md bg-muted/60', isCompact ? 'h-2' : 'h-2.5')}
            style={{ width: `${w}%` }}
            animate={{ opacity: [0.3, 0.6, 0.3] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              delay: i * 0.2,
              ease: 'easeInOut',
            }}
          />
        ))}
      </div>
    </motion.div>
  )
}
