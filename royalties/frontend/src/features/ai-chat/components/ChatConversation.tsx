/** ChatConversation — scrollable message area with auto-scroll, shimmer, error, thinking blocks, follow-up suggestions, and sources. */

import { useRef, useEffect, useCallback, useState, type ReactNode } from 'react'
import { AnimatePresence } from 'motion/react'
import { cn } from '@/lib/utils'
import { ChatMessage } from './ChatMessage'
import { ChatShimmer } from './ChatShimmer'
import { ChatTypingIndicator } from './ChatTypingIndicator'
import { ChatScrollButton } from './ChatScrollButton'
import { ChatEmptyState } from './ChatEmptyState'
import { ChatErrorState } from './ChatErrorState'
import { ChatThinking } from './ChatThinking'
import { ChatSuggestionChips } from './ChatSuggestionChips'
import { ChatSources } from './ChatSources'
import type { ChatSource } from './ChatSources'
import type { ChatMessageData, ChatSuggestion } from '../types'

/** Strip document injection from user display text */
function cleanUserDisplay(rawText: string): string {
  if (!rawText.includes('--- Document:')) return rawText

  const match = rawText.match(/User question:\s*(.+)$/s)
  if (match?.[1]?.trim()) return match[1].trim()

  const docPattern = /\n?\n?--- Document: (.+?) ---[\s\S]*?--- End of \1 ---/g
  const docNames: string[] = []
  let m: RegExpExecArray | null
  while ((m = docPattern.exec(rawText)) !== null) {
    docNames.push(m[1])
  }
  let cleaned = rawText.replace(/\n?\n?--- Document: .+? ---[\s\S]*?--- End of .+? ---/g, '').trim()

  if (docNames.length > 0) {
    const label = docNames.map((n) => `📎 ${n}`).join('\n')
    cleaned = cleaned ? `${cleaned}\n\n${label}` : label
  }

  return cleaned || '(Document analysis request)'
}

/** Extract thinking/reasoning content from message parts */
function extractThinking(parts?: { type: string; content?: string }[]): string | null {
  if (!parts) return null
  const thinkParts = parts.filter((p) => p.type === 'thinking' || p.type === 'reasoning')
  if (thinkParts.length === 0) return null
  return thinkParts.map((p) => p.content || '').join('\n')
}

/** Extract sources from message parts */
function extractSources(parts?: { type: string; content?: string }[]): ChatSource[] {
  if (!parts) return []
  return parts
    .filter((p) => p.type === 'source')
    .map((p) => {
      try {
        return JSON.parse(p.content || '{}') as ChatSource
      } catch {
        return { title: p.content || 'Source' }
      }
    })
}

interface ChatConversationProps {
  messages: ChatMessageData[]
  isLoading: boolean
  variant?: 'compact' | 'full'
  /** Suggestions shown in empty state */
  suggestions?: ChatSuggestion[]
  onSuggestionClick?: (text: string) => void
  /** Follow-up suggestions after the last assistant response */
  followUpSuggestions?: ChatSuggestion[]
  /** Empty state config */
  emptyTitle?: string
  emptyDescription?: string
  emptyContextLabel?: string
  showUploadHint?: boolean
  /** Error state */
  error?: string | null
  onRetry?: () => void
  /** Extra content below messages */
  children?: ReactNode
}

export function ChatConversation({
  messages,
  isLoading,
  variant = 'full',
  suggestions = [],
  onSuggestionClick,
  followUpSuggestions = [],
  emptyTitle,
  emptyDescription,
  emptyContextLabel,
  showUploadHint = false,
  error,
  onRetry,
  children,
}: ChatConversationProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const isCompact = variant === 'compact'
  const hasMessages = messages.length > 0

  // Determine if the last assistant message is still streaming (has parts)
  const lastMsg = messages[messages.length - 1]
  const isStreaming = isLoading && lastMsg?.role === 'assistant'
  const isWaitingForFirstToken = isLoading && (!lastMsg || lastMsg.role === 'user')

  // Show follow-up suggestions only when: has messages, not loading, last message is assistant
  const showFollowUps =
    !isLoading && followUpSuggestions.length > 0 && lastMsg?.role === 'assistant'

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const el = e.currentTarget
      const threshold = isCompact ? 60 : 80
      setShowScrollBtn(el.scrollHeight - el.scrollTop - el.clientHeight > threshold)
    },
    [isCompact],
  )

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  return (
    <div className="relative flex-1 overflow-hidden min-h-0">
      <div ref={scrollRef} onScroll={handleScroll} className="h-full overflow-y-auto scroll-smooth">
        {!hasMessages && !error ? (
          <ChatEmptyState
            variant={variant}
            title={emptyTitle}
            description={emptyDescription}
            contextLabel={emptyContextLabel}
            suggestions={suggestions}
            onSuggestionClick={onSuggestionClick ?? (() => {})}
            showUploadHint={showUploadHint}
          />
        ) : (
          <div
            className={cn(
              'space-y-2',
              isCompact ? 'px-3 py-3' : 'max-w-3xl mx-auto px-4 py-6 space-y-1',
            )}
          >
            <AnimatePresence initial={false}>
              {messages.map((msg, idx) => {
                const textParts = msg.parts?.filter((p: { type: string }) => p.type === 'text')
                const rawText =
                  textParts
                    ?.map((p: { type: string; content?: string }) => p.content || '')
                    .join('') || ''
                if (!rawText) return null

                const isUser = msg.role === 'user'
                const displayText = isUser ? cleanUserDisplay(rawText) : rawText
                const isLastAssistant = !isUser && idx === messages.length - 1

                // Extract thinking & sources from parts
                const thinkingContent = !isUser ? extractThinking(msg.parts) : null
                const sources = !isUser ? extractSources(msg.parts) : []

                return (
                  <div key={msg.id}>
                    {/* Thinking/reasoning block before the message */}
                    {thinkingContent && (
                      <ChatThinking
                        content={thinkingContent}
                        variant={variant}
                        isStreaming={isLastAssistant && isStreaming}
                      />
                    )}

                    <ChatMessage
                      role={msg.role}
                      content={displayText}
                      variant={variant}
                      isLatest={isLastAssistant}
                      animationDelay={idx === messages.length - 1 ? 0.05 : 0}
                      createdAt={msg.createdAt}
                      status={isLastAssistant && isStreaming ? 'streaming' : msg.status}
                      error={msg.error}
                      onRetry={isLastAssistant ? onRetry : undefined}
                    />

                    {/* Sources after assistant messages */}
                    {sources.length > 0 && <ChatSources sources={sources} variant={variant} />}
                  </div>
                )
              })}
            </AnimatePresence>

            {/* Shimmer: waiting for first token from the model */}
            <AnimatePresence>
              {isWaitingForFirstToken && <ChatShimmer variant={variant} />}
            </AnimatePresence>

            {/* Typing indicator: visible while actively streaming content */}
            {isStreaming && <ChatTypingIndicator variant={variant} />}

            {/* Follow-up suggestion chips after last assistant message */}
            {showFollowUps && onSuggestionClick && (
              <ChatSuggestionChips
                suggestions={followUpSuggestions}
                onSelect={onSuggestionClick}
                variant={variant}
              />
            )}

            {/* Conversation-level error */}
            <AnimatePresence>
              {error && !isLoading && (
                <ChatErrorState message={error} onRetry={onRetry} variant={variant} />
              )}
            </AnimatePresence>

            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <ChatScrollButton
        visible={showScrollBtn && hasMessages}
        onClick={scrollToBottom}
        variant={variant}
      />

      {children}
    </div>
  )
}
