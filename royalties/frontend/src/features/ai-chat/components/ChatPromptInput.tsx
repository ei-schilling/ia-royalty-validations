/** ChatPromptInput — rich input area with file attachments, image paste, mode toggle, keyboard shortcuts, and send/stop controls. */

import { useRef, useCallback, useEffect, type FormEvent, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import {
  Send,
  StopCircle,
  Paperclip,
  Eraser,
  Database,
  Search,
  Sparkles,
  CheckCircle2,
  X,
} from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { ChatFileChip } from './ChatFileChip'

interface ChatPromptInputProps {
  variant?: 'compact' | 'full'
  placeholder?: string
  isLoading: boolean
  hasMessages: boolean

  onSubmit: (text: string) => void
  onStop: () => void
  onClear: () => void

  /** File upload features */
  enableFileUpload?: boolean
  attachedFiles?: File[]
  uploadStates?: Record<string, 'pending' | 'uploading' | 'done' | 'error'>
  uploadedDocs?: { name: string }[]
  onAddFiles?: (files: FileList | File[]) => void
  onRemoveFile?: (index: number) => void
  onRemoveUploadedDoc?: (name: string) => void

  /** Mode toggle */
  enableModeToggle?: boolean
  chatMode?: 'query' | 'agent'
  onToggleMode?: () => void

  /** Drag & drop */
  isDragging?: boolean
  onDragOver?: (e: DragEvent) => void
  onDragLeave?: (e: DragEvent) => void
  onDrop?: (e: DragEvent) => void

  /** ArrowUp-to-edit: last user message text */
  lastUserMessage?: string
}

export function ChatPromptInput({
  variant = 'full',
  placeholder,
  isLoading,
  hasMessages,
  onSubmit,
  onStop,
  onClear,
  enableFileUpload = false,
  attachedFiles = [],
  uploadStates = {},
  uploadedDocs = [],
  onAddFiles,
  onRemoveFile,
  onRemoveUploadedDoc,
  enableModeToggle = false,
  chatMode = 'query',
  onToggleMode,
  lastUserMessage,
}: ChatPromptInputProps) {
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const isCompact = variant === 'compact'

  const handleSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault()
      const value = inputRef.current?.value.trim()
      if (!value && attachedFiles.length === 0) return
      if (isLoading) return
      onSubmit(value || '')
      if (inputRef.current) inputRef.current.value = ''
      // Reset textarea height
      if (inputRef.current) inputRef.current.style.height = 'auto'
    },
    [onSubmit, isLoading, attachedFiles.length],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSubmit(e)
        return
      }
      // Escape: stop generating or blur
      if (e.key === 'Escape') {
        if (isLoading) {
          e.preventDefault()
          onStop()
        } else {
          inputRef.current?.blur()
        }
        return
      }
      // ArrowUp in empty input: load last user message for editing
      if (
        e.key === 'ArrowUp' &&
        lastUserMessage &&
        inputRef.current &&
        inputRef.current.value === '' &&
        inputRef.current.selectionStart === 0
      ) {
        e.preventDefault()
        inputRef.current.value = lastUserMessage
        inputRef.current.style.height = 'auto'
        const maxH = isCompact ? 100 : 160
        inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, maxH) + 'px'
        // Place cursor at the end
        const len = lastUserMessage.length
        inputRef.current.setSelectionRange(len, len)
      }
    },
    [handleSubmit, isLoading, onStop, lastUserMessage, isCompact],
  )

  const handleInput = useCallback(() => {
    if (!inputRef.current) return
    inputRef.current.style.height = 'auto'
    const maxH = isCompact ? 100 : 160
    inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, maxH) + 'px'
  }, [isCompact])

  /** Handle image paste from clipboard */
  const handlePaste = useCallback(
    (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
      if (!enableFileUpload || !onAddFiles) return
      const items = Array.from(e.clipboardData.items)
      const imageFiles = items
        .filter((item) => item.type.startsWith('image/'))
        .map((item) => item.getAsFile())
        .filter((f): f is File => f !== null)
      if (imageFiles.length > 0) {
        onAddFiles(imageFiles)
      }
    },
    [enableFileUpload, onAddFiles],
  )

  // Global Ctrl+/ or Cmd+/ to focus input
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── Compact variant (sidebar) ──
  if (isCompact) {
    return (
      <div className="px-3 py-2 border-t border-border/50 shrink-0">
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={placeholder ?? 'Ask a question…'}
            rows={1}
            className="flex-1 rounded-lg border border-border/50 bg-background/50 px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/30 resize-none min-h-[28px] max-h-[100px]"
          />
          {isLoading ? (
            <button
              type="button"
              onClick={onStop}
              className="h-7 w-7 rounded-lg bg-destructive/10 text-destructive flex items-center justify-center hover:bg-destructive/20 transition-colors shrink-0"
              aria-label="Stop generating"
            >
              <StopCircle className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              type="submit"
              className="h-7 w-7 rounded-lg bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition-colors shrink-0 disabled:opacity-50"
              disabled={isLoading}
              aria-label="Send message"
            >
              <Send className="h-3 w-3" />
            </button>
          )}
        </form>
      </div>
    )
  }

  // ── Full variant (page) ──
  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.4 }}
        className="mt-3 relative"
      >
        {/* Uploaded file badges */}
        <AnimatePresence>
          {uploadedDocs.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex flex-wrap gap-1.5 mb-2"
            >
              {uploadedDocs.map((doc) => (
                <Badge key={doc.name} variant="secondary" className="text-[10px] gap-1 pr-1">
                  <CheckCircle2 className="h-2.5 w-2.5 text-emerald-400" />
                  {doc.name}
                  {onRemoveUploadedDoc && (
                    <button
                      onClick={() => onRemoveUploadedDoc(doc.name)}
                      className="ml-0.5 hover:text-foreground"
                      aria-label={`Remove ${doc.name}`}
                    >
                      <X className="h-2.5 w-2.5" />
                    </button>
                  )}
                </Badge>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Attached files (pre-upload) */}
        <AnimatePresence>
          {attachedFiles.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="flex flex-wrap gap-2 mb-2"
            >
              {attachedFiles.map((file, i) => (
                <ChatFileChip
                  key={file.name + file.size}
                  file={file}
                  status={uploadStates[file.name + file.size] || 'pending'}
                  onRemove={onRemoveFile ? () => onRemoveFile(i) : undefined}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input bar */}
        <form onSubmit={handleSubmit} className="relative">
          <div className="flex items-end gap-2 rounded-2xl border border-border/50 bg-card/60 backdrop-blur-sm shadow-sm focus-within:border-primary/40 focus-within:shadow-md focus-within:shadow-primary/5 transition-all">
            {/* Attach button */}
            {enableFileUpload && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="p-3 pb-3.5 text-muted-foreground/60 hover:text-primary transition-colors shrink-0"
                    aria-label="Attach file"
                  >
                    <Paperclip className="h-4 w-4" />
                  </button>
                </TooltipTrigger>
                <TooltipContent>Attach a file</TooltipContent>
              </Tooltip>
            )}

            {enableFileUpload && (
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                accept=".csv,.xlsx,.xls,.json,.pdf,.txt,.md,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp,.bmp,.svg"
                multiple
                onChange={(e) => e.target.files && onAddFiles?.(e.target.files)}
              />
            )}

            <textarea
              ref={inputRef}
              placeholder={placeholder ?? 'Ask something…'}
              rows={1}
              onKeyDown={handleKeyDown}
              onInput={handleInput}
              onPaste={handlePaste}
              className={cn(
                'flex-1 resize-none bg-transparent py-3.5 text-sm text-foreground placeholder:text-muted-foreground/40 focus:outline-none min-h-[44px] max-h-[160px] leading-relaxed',
                !enableFileUpload && 'pl-4',
              )}
            />

            {/* Action buttons */}
            <div className="flex items-center gap-1 pr-2 pb-2.5">
              {/* Mode toggle */}
              {enableModeToggle && onToggleMode && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={onToggleMode}
                      className={cn(
                        'p-1.5 rounded-lg transition-all flex items-center gap-1',
                        chatMode === 'agent'
                          ? 'text-primary bg-primary/10 ring-1 ring-primary/30'
                          : 'text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50',
                      )}
                    >
                      {chatMode === 'agent' ? (
                        <Database className="h-3.5 w-3.5" />
                      ) : (
                        <Search className="h-3.5 w-3.5" />
                      )}
                      <span className="text-[10px] font-medium uppercase tracking-wider pr-0.5">
                        {chatMode === 'agent' ? 'SQL' : 'RAG'}
                      </span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {chatMode === 'agent'
                      ? 'Agent mode: can query the database'
                      : 'RAG mode: searches documents'}
                  </TooltipContent>
                </Tooltip>
              )}

              {/* Clear button */}
              {hasMessages && !isLoading && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={onClear}
                      className="p-1.5 rounded-lg text-muted-foreground/50 hover:text-muted-foreground hover:bg-muted/50 transition-all"
                      aria-label="Clear chat"
                    >
                      <Eraser className="h-3.5 w-3.5" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>Clear chat</TooltipContent>
                </Tooltip>
              )}

              {/* Stop / Send */}
              {isLoading ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={onStop}
                      className="p-2 rounded-xl bg-destructive/10 text-destructive hover:bg-destructive/20 transition-all"
                      aria-label="Stop generating"
                    >
                      <StopCircle className="h-4 w-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>Stop</TooltipContent>
                </Tooltip>
              ) : (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="submit"
                      className="p-2 rounded-xl bg-primary text-primary-foreground hover:brightness-110 transition-all shadow-sm"
                      aria-label="Send message"
                    >
                      <Send className="h-4 w-4" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>Send message</TooltipContent>
                </Tooltip>
              )}
            </div>
          </div>
        </form>

        {/* Footer */}
        <div className="flex items-center justify-between mt-2.5 px-1">
          <div className="flex items-center gap-3">
            <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[9px] text-muted-foreground/30 font-mono">
              <span className="px-1 py-0.5 rounded border border-border/30 bg-muted/20">Ctrl</span>
              <span>+</span>
              <span className="px-1 py-0.5 rounded border border-border/30 bg-muted/20">/</span>
              <span className="ml-1">focus</span>
            </kbd>
            <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[9px] text-muted-foreground/30 font-mono">
              <span className="px-1 py-0.5 rounded border border-border/30 bg-muted/20">↑</span>
              <span className="ml-1">edit</span>
            </kbd>
          </div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-3 w-3 text-muted-foreground/30" />
            <span className="text-[10px] text-muted-foreground/30 tracking-wide">
              Powered by your royalty knowledge base
            </span>
          </div>
        </div>
      </motion.div>
    </TooltipProvider>
  )
}
