/** ChatErrorState — inline error display with retry action. */

import { motion } from 'motion/react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatErrorStateProps {
  message?: string
  onRetry?: () => void
  variant?: 'compact' | 'full'
}

export function ChatErrorState({
  message = 'Something went wrong. Please try again.',
  onRetry,
  variant = 'full',
}: ChatErrorStateProps) {
  const isCompact = variant === 'compact'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      className={cn(
        'flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5',
        isCompact ? 'mx-3 p-3' : 'mx-auto max-w-3xl p-4',
      )}
    >
      <div className="shrink-0 mt-0.5">
        <div
          className={cn(
            'rounded-lg bg-destructive/10 flex items-center justify-center',
            isCompact ? 'w-6 h-6' : 'w-8 h-8',
          )}
        >
          <AlertTriangle className={cn('text-destructive', isCompact ? 'h-3 w-3' : 'h-4 w-4')} />
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <p
          className={cn(
            'text-destructive/90 leading-relaxed',
            isCompact ? 'text-[11px]' : 'text-sm',
          )}
        >
          {message}
        </p>

        {onRetry && (
          <button
            onClick={onRetry}
            className={cn(
              'mt-2 inline-flex items-center gap-1.5 rounded-lg font-medium transition-colors',
              'text-destructive hover:text-destructive/80 hover:bg-destructive/10',
              isCompact ? 'text-[10px] px-2 py-1' : 'text-xs px-3 py-1.5',
            )}
          >
            <RefreshCw className={cn(isCompact ? 'h-2.5 w-2.5' : 'h-3 w-3')} />
            Try again
          </button>
        )}
      </div>
    </motion.div>
  )
}
