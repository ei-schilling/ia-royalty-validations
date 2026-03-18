/** Help page — premium AI chat assistant with markdown + file upload.
 *  Now uses shared ai-chat feature components. */

import { useState, useCallback, useMemo, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { Paperclip } from 'lucide-react'
import { useChat, fetchServerSentEvents } from '@tanstack/ai-react'
import { ChatConversation, ChatPromptInput } from '@/features/ai-chat'
import type { ChatSuggestion, ChatMessageData } from '@/features/ai-chat'

/* ─── Suggestions ────────────────────────────────────── */
const SUGGESTIONS: ChatSuggestion[] = [
  { icon: '📊', text: 'What are common royalty rate structures?' },
  { icon: '✅', text: 'How do I validate royalty amounts?' },
  { icon: '🔄', text: 'Explain the settlement reconciliation process' },
  { icon: '⚠️', text: 'What causes duplicate entries in statements?' },
  { icon: '📋', text: 'Summarize best practices for royalty reporting' },
  { icon: '🔍', text: 'What validation rules does this system check?' },
]

/** Dynamic follow-up suggestions based on conversation context */
const FOLLOW_UP_SUGGESTIONS: ChatSuggestion[] = [
  { icon: '🔎', text: 'Tell me more about that' },
  { icon: '📈', text: 'Can you show an example?' },
  { icon: '📄', text: 'How does this apply to my documents?' },
]

/* ─── Main component ─────────────────────────────────── */
export default function HelpPage() {
  const [attachedFiles, setAttachedFiles] = useState<File[]>([])
  const [uploadStates, setUploadStates] = useState<
    Record<string, 'pending' | 'uploading' | 'done' | 'error'>
  >({})
  const [uploadedDocs, setUploadedDocs] = useState<
    { name: string; contentFull?: string; type?: string }[]
  >([])
  const [isDragging, setIsDragging] = useState(false)
  const [chatMode, setChatMode] = useState<'query' | 'agent'>('query')

  const connection = useMemo(
    () => fetchServerSentEvents(`/api/chat/stream?mode=${chatMode}`),
    [chatMode],
  )

  const { messages, sendMessage, isLoading, stop, clear } = useChat({ connection })

  /* ── File upload logic ── */
  async function uploadFile(
    file: File,
  ): Promise<{ name: string; contentFull?: string; type?: string } | null> {
    const key = file.name + file.size
    setUploadStates((s) => ({ ...s, [key]: 'uploading' }))
    try {
      const fd = new FormData()
      fd.append('file', file)
      const resp = await fetch('/api/chat/upload', { method: 'POST', body: fd })
      const data = await resp.json()
      if (data.success) {
        setUploadStates((s) => ({ ...s, [key]: 'done' }))
        const doc = {
          name: file.name,
          contentFull: data.document?.contentFull as string | undefined,
          type: data.document?.type as string | undefined,
        }
        setUploadedDocs((prev) => [...prev, doc])
        return doc
      }
      setUploadStates((s) => ({ ...s, [key]: 'error' }))
      return null
    } catch {
      setUploadStates((s) => ({ ...s, [key]: 'error' }))
      return null
    }
  }

  const addFiles = useCallback((files: FileList | File[]) => {
    const newFiles = Array.from(files)
    setAttachedFiles((prev) => [...prev, ...newFiles])
    newFiles.forEach((f) => {
      setUploadStates((s) => ({ ...s, [f.name + f.size]: 'pending' }))
    })
  }, [])

  const removeFile = useCallback((index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const removeUploadedDoc = useCallback((name: string) => {
    setUploadedDocs((prev) => prev.filter((d) => d.name !== name))
  }, [])

  /* ── Drag & drop ── */
  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault()
    if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
    },
    [addFiles],
  )

  /* ── Submit ── */
  const handleSubmit = useCallback(
    async (text: string) => {
      if (!text && attachedFiles.length === 0) return

      // Upload pending files
      const pending = attachedFiles.filter((f) => uploadStates[f.name + f.size] === 'pending')
      let freshDocs: { name: string; contentFull?: string; type?: string }[] = []
      if (pending.length > 0) {
        const results = await Promise.all(pending.map(uploadFile))
        freshDocs = results.filter(Boolean) as typeof freshDocs
      }

      const allDocs = [
        ...uploadedDocs.filter((d) => !freshDocs.some((f) => f.name === d.name)),
        ...freshDocs,
      ]

      let messageText = text || ''
      if (allDocs.length > 0) {
        const docBlocks = allDocs
          .filter((d) => d.contentFull)
          .map((d) => `--- Document: ${d.name} ---\n${d.contentFull}\n--- End of ${d.name} ---`)

        if (docBlocks.length > 0) {
          const instruction =
            messageText ||
            `Please analyze ${allDocs.length > 1 ? 'these documents' : 'this document'} and provide a detailed summary.`
          messageText = `${instruction}\n\n${docBlocks.join('\n\n')}`
        } else if (!messageText) {
          const names = allDocs.map((d) => `"${d.name}"`).join(', ')
          messageText = `I've uploaded ${names}. Please analyze ${allDocs.length > 1 ? 'these documents' : 'this document'} and provide a summary.`
        }
      }

      if (messageText) {
        sendMessage(messageText)
      }
      setAttachedFiles([])
      setUploadStates({})
      setUploadedDocs([])
    },
    [attachedFiles, uploadStates, uploadedDocs, sendMessage],
  )

  const handleClear = useCallback(() => {
    clear()
    setUploadedDocs([])
  }, [clear])

  const toggleMode = useCallback(() => {
    setChatMode((m) => (m === 'query' ? 'agent' : 'query'))
  }, [])

  const hasMessages = messages.length > 0

  // Find last user message text for ArrowUp-to-edit
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
    <div
      className="flex flex-col h-[calc(100vh-10rem)] relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      <AnimatePresence>
        {isDragging && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 flex items-center justify-center rounded-2xl border-2 border-dashed border-primary/50 bg-primary/5 backdrop-blur-sm"
          >
            <div className="flex flex-col items-center gap-3">
              <motion.div
                animate={{ y: [0, -8, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center"
              >
                <Paperclip className="h-7 w-7 text-primary" />
              </motion.div>
              <p className="text-sm font-medium text-foreground">Drop files here</p>
              <p className="text-xs text-muted-foreground">CSV, XLSX, JSON, PDF, TXT, MD, images</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Conversation */}
      <ChatConversation
        messages={messages as ChatMessageData[]}
        isLoading={isLoading}
        variant="full"
        suggestions={SUGGESTIONS}
        onSuggestionClick={(text) => sendMessage(text)}
        followUpSuggestions={FOLLOW_UP_SUGGESTIONS}
        emptyTitle="Royalty Assistant"
        emptyDescription="Ask about royalty settlements, upload documents for analysis, or get help with validation rules."
        showUploadHint
      />

      {/* Input */}
      <ChatPromptInput
        variant="full"
        placeholder="Ask something or drop a file…"
        isLoading={isLoading}
        hasMessages={hasMessages}
        onSubmit={handleSubmit}
        onStop={stop}
        onClear={handleClear}
        enableFileUpload
        attachedFiles={attachedFiles}
        uploadStates={uploadStates}
        uploadedDocs={uploadedDocs}
        onAddFiles={addFiles}
        onRemoveFile={removeFile}
        onRemoveUploadedDoc={removeUploadedDoc}
        enableModeToggle
        chatMode={chatMode}
        onToggleMode={toggleMode}
        lastUserMessage={lastUserMessage}
      />
    </div>
  )
}
