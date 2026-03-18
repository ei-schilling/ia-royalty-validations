/** ChatMessageActions — copy / like / dislike / regenerate action buttons below assistant messages */

import { useState, useCallback } from 'react'
import { Copy, Check, ThumbsUp, ThumbsDown, RefreshCw } from 'lucide-react'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface ChatMessageActionsProps {
  content: string
  className?: string
  /** Callback to regenerate the last assistant message */
  onRetry?: () => void
}

export function ChatMessageActions({ content, className, onRetry }: ChatMessageActionsProps) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<'like' | 'dislike' | null>(null)

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [content])

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.3, duration: 0.2 }}
      className={cn('flex items-center gap-0.5', className)}
    >
      <button
        onClick={handleCopy}
        className="p-1.5 rounded-md text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50 transition-all"
        aria-label="Copy response"
      >
        {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
      </button>

      {onRetry && (
        <button
          onClick={onRetry}
          className="p-1.5 rounded-md text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50 transition-all"
          aria-label="Regenerate response"
        >
          <RefreshCw className="h-3 w-3" />
        </button>
      )}

      <button
        onClick={() => setFeedback(feedback === 'like' ? null : 'like')}
        className={cn(
          'p-1.5 rounded-md transition-all',
          feedback === 'like'
            ? 'text-emerald-400 bg-emerald-500/10'
            : 'text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50',
        )}
        aria-label="Like response"
      >
        <ThumbsUp className="h-3 w-3" />
      </button>
      <button
        onClick={() => setFeedback(feedback === 'dislike' ? null : 'dislike')}
        className={cn(
          'p-1.5 rounded-md transition-all',
          feedback === 'dislike'
            ? 'text-rose-400 bg-rose-500/10'
            : 'text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50',
        )}
        aria-label="Dislike response"
      >
        <ThumbsDown className="h-3 w-3" />
      </button>
    </motion.div>
  )
}
