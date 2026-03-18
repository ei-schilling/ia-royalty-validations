/** ChatSources — renders source citations / references from RAG retrieval. */

import { motion } from 'motion/react'
import { FileText, ExternalLink, Hash } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface ChatSource {
  title: string
  /** URL or document identifier */
  url?: string
  /** Relevant snippet/excerpt */
  snippet?: string
  /** Page or section number */
  page?: number | string
  /** Relevance score 0-1 */
  score?: number
}

interface ChatSourcesProps {
  sources: ChatSource[]
  variant?: 'compact' | 'full'
}

export function ChatSources({ sources, variant = 'full' }: ChatSourcesProps) {
  const isCompact = variant === 'compact'

  if (sources.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: 0.3 }}
      className={cn('mt-2', isCompact ? 'ml-8' : 'ml-11')}
    >
      <div
        className={cn(
          'text-muted-foreground/50 font-medium uppercase tracking-wider mb-1.5',
          isCompact ? 'text-[8px]' : 'text-[9px]',
        )}
      >
        Sources
      </div>

      <div className={cn('flex flex-wrap gap-1.5', isCompact ? 'gap-1' : 'gap-1.5')}>
        {sources.map((source, i) => (
          <SourceChip key={i} source={source} index={i + 1} variant={variant} />
        ))}
      </div>
    </motion.div>
  )
}

function SourceChip({
  source,
  index,
  variant = 'full',
}: {
  source: ChatSource
  index: number
  variant?: 'compact' | 'full'
}) {
  const isCompact = variant === 'compact'
  const hasLink = !!source.url

  const Wrapper = hasLink ? 'a' : 'div'
  const wrapperProps = hasLink
    ? { href: source.url, target: '_blank', rel: 'noopener noreferrer' }
    : {}

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.35 + index * 0.04 }}
    >
      <Wrapper
        {...wrapperProps}
        className={cn(
          'group/source inline-flex items-center gap-1.5 rounded-lg border border-border/40',
          'bg-card/60 transition-all',
          hasLink && 'cursor-pointer hover:border-primary/30 hover:bg-primary/5',
          isCompact ? 'px-2 py-1' : 'px-2.5 py-1.5',
        )}
      >
        {/* Index badge */}
        <span
          className={cn(
            'inline-flex items-center justify-center rounded-md bg-muted/60 font-mono font-medium text-muted-foreground/70',
            isCompact ? 'w-3.5 h-3.5 text-[7px]' : 'w-4 h-4 text-[8px]',
          )}
        >
          {index}
        </span>

        {/* Icon */}
        <FileText
          className={cn('text-muted-foreground/40 shrink-0', isCompact ? 'h-2.5 w-2.5' : 'h-3 w-3')}
        />

        {/* Title + page */}
        <span
          className={cn(
            'truncate max-w-[120px] text-muted-foreground group-hover/source:text-foreground transition-colors',
            isCompact ? 'text-[9px]' : 'text-[10px]',
          )}
        >
          {source.title}
        </span>

        {source.page != null && (
          <span
            className={cn(
              'flex items-center gap-0.5 text-muted-foreground/40 shrink-0',
              isCompact ? 'text-[8px]' : 'text-[9px]',
            )}
          >
            <Hash className={cn(isCompact ? 'h-2 w-2' : 'h-2.5 w-2.5')} />
            {source.page}
          </span>
        )}

        {hasLink && (
          <ExternalLink
            className={cn(
              'text-muted-foreground/30 group-hover/source:text-primary/60 shrink-0 transition-colors',
              isCompact ? 'h-2 w-2' : 'h-2.5 w-2.5',
            )}
          />
        )}
      </Wrapper>
    </motion.div>
  )
}
