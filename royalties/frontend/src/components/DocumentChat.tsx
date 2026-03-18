/** Document-context chat — compact AI assistant with document injected as context.
 *  Now uses shared ai-chat feature components. */

import { useRef, useMemo, useCallback } from 'react'
import { useChat, fetchServerSentEvents } from '@tanstack/ai-react'
import { Bot, Eraser } from 'lucide-react'
import { ChatConversation } from '@/features/ai-chat'
import { ChatPromptInput } from '@/features/ai-chat'
import type { ChatSuggestion, ChatMessageData } from '@/features/ai-chat'

/* ─── Suggestions for document analysis ──────────────── */
const DOC_SUGGESTIONS: ChatSuggestion[] = [
  { icon: '📝', text: 'Summarize the key data in this document' },
  { icon: '⚠️', text: 'Are there any anomalies or errors?' },
  { icon: '💰', text: 'What royalty rates are used?' },
  { icon: '🔢', text: 'List all unique ISBNs or product identifiers' },
]

const DOC_FOLLOW_UPS: ChatSuggestion[] = [
  { icon: '🔍', text: 'Show more details' },
  { icon: '📉', text: 'Find discrepancies' },
  { icon: '📊', text: 'Compare with expected values' },
]

/* ─── Props ──────────────────────────────────────────── */
interface Props {
  documentContent: string
  filename: string
}

export default function DocumentChat({ documentContent, filename }: Props) {
  const documentInjected = useRef(false)

  const connection = useMemo(() => fetchServerSentEvents('/api/chat/stream?mode=query'), [])
  const { messages, sendMessage, isLoading, stop, clear } = useChat({ connection })

  /** Build a message that includes document context (first message only). */
  const sendWithContext = useCallback(
    (text: string) => {
      if (!text) return
      if (!documentInjected.current && documentContent) {
        const docSlice = documentContent.slice(0, 400_000)
        const contextMessage =
          `The user is viewing a royalty statement file named "${filename}". ` +
          `Here is the full content of the document:\n\n` +
          `--- Document: ${filename} ---\n${docSlice}\n--- End of ${filename} ---\n\n` +
          `Please answer the following question based primarily on this document. ` +
          `If the information in the document is not sufficient, you may use your knowledge base (RAG) about royalty settlements to enrich your answer.\n\n` +
          `User question: ${text}`
        documentInjected.current = true
        sendMessage(contextMessage)
      } else {
        sendMessage(text)
      }
    },
    [documentContent, filename, sendMessage],
  )

  const handleClear = useCallback(() => {
    clear()
    documentInjected.current = false
  }, [clear])

  const hasMessages = messages.length > 0

  // Last user message for ArrowUp editing
  const lastUserMessage = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i] as ChatMessageData
      if (msg.role === 'user') {
        const text = msg.parts
          ?.filter((p: { type: string }) => p.type === 'text')
          .map((p: { type: string; content?: string }) => p.content || '')
          .join('')
        if (text) return text
      }
    }
    return undefined
  }, [messages])

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50 shrink-0">
        <div className="w-5 h-5 rounded-md bg-primary/10 flex items-center justify-center">
          <Bot className="h-3 w-3 text-primary" />
        </div>
        <span className="text-xs font-medium text-foreground flex-1">Document Assistant</span>
        {hasMessages && (
          <button
            onClick={handleClear}
            className="p-1 rounded hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            title="Clear chat"
          >
            <Eraser className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Conversation */}
      <ChatConversation
        messages={messages as ChatMessageData[]}
        isLoading={isLoading}
        variant="compact"
        suggestions={DOC_SUGGESTIONS}
        onSuggestionClick={sendWithContext}
        followUpSuggestions={DOC_FOLLOW_UPS}
        emptyContextLabel={filename}
      />

      {/* Input */}
      <ChatPromptInput
        variant="compact"
        placeholder={`Ask about ${filename}…`}
        isLoading={isLoading}
        hasMessages={hasMessages}
        onSubmit={sendWithContext}
        onStop={stop}
        onClear={handleClear}
        lastUserMessage={lastUserMessage}
      />
    </div>
  )
}
