/** AI Chat feature — shared components for Document Assistant & Royalty Assistant */

export { ChatConversation } from './components/ChatConversation'
export { ChatMessage } from './components/ChatMessage'
export { ChatMarkdown } from './components/ChatMarkdown'
export { ChatPromptInput } from './components/ChatPromptInput'
export { ChatEmptyState } from './components/ChatEmptyState'
export { ChatFileChip } from './components/ChatFileChip'
export { ChatTypingIndicator } from './components/ChatTypingIndicator'
export { ChatScrollButton } from './components/ChatScrollButton'
export { ChatMessageActions } from './components/ChatMessageActions'
export { ChatShimmer } from './components/ChatShimmer'
export { ChatErrorState } from './components/ChatErrorState'
export { ChatThinking } from './components/ChatThinking'
export { ChatSuggestionChips } from './components/ChatSuggestionChips'
export { ChatSources } from './components/ChatSources'

export { useChatKeyboard } from './hooks/useChatKeyboard'

export type {
  ChatConfig,
  ChatMessageData,
  ChatFileData,
  ChatSuggestion,
  MessageStatus,
} from './types'
export type { ChatSource } from './components/ChatSources'
