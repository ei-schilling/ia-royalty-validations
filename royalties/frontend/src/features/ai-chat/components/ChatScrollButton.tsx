/** ChatScrollButton — floating scroll-to-bottom button. */

import { motion, AnimatePresence } from 'motion/react'
import { ArrowDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ChatScrollButtonProps {
  visible: boolean
  onClick: () => void
  variant?: 'compact' | 'full'
}

export function ChatScrollButton({ visible, onClick, variant = 'full' }: ChatScrollButtonProps) {
  const isCompact = variant === 'compact'

  return (
    <AnimatePresence>
      {visible && (
        <motion.button
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          onClick={onClick}
          className={cn(
            'absolute left-1/2 -translate-x-1/2 z-10 rounded-full bg-card border border-border/50 shadow-lg flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors',
            isCompact ? 'bottom-16 w-6 h-6' : 'bottom-32 w-8 h-8',
          )}
          aria-label="Scroll to bottom"
        >
          <ArrowDown className={cn(isCompact ? 'h-3 w-3' : 'h-3.5 w-3.5')} />
        </motion.button>
      )}
    </AnimatePresence>
  )
}
