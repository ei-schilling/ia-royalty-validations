/** Shared types for AI chat feature */

export type MessageStatus = 'sending' | 'streaming' | 'done' | 'error'

export interface ChatMessageData {
  id: string
  role: 'user' | 'assistant'
  parts?: { type: string; content?: string }[]
  /** Timestamp when the message was created (ISO string or epoch ms) */
  createdAt?: string | number
  /** Current status of this message */
  status?: MessageStatus
  /** Error details if status === 'error' */
  error?: string
}

export interface ChatFileData {
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
}

export interface ChatSuggestion {
  icon: string
  text: string
}

export interface ChatConfig {
  /** Variant controls sizing: 'compact' for sidebar, 'full' for full-page */
  variant: 'compact' | 'full'
  /** Title displayed in the header area */
  title?: string
  /** Placeholder text for the input */
  placeholder?: string
  /** Show file upload capabilities */
  enableFileUpload?: boolean
  /** Show mode toggle (RAG / SQL Agent) */
  enableModeToggle?: boolean
  /** Available suggestions for the empty state */
  suggestions?: ChatSuggestion[]
  /** Custom empty state description */
  emptyDescription?: string
  /** File types accepted for upload */
  acceptedFileTypes?: string
}
