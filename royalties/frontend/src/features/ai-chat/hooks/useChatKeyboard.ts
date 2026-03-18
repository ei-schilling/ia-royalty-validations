/** useChatKeyboard — keyboard shortcuts for the AI chat interface.
 *
 *  Shortcuts:
 *  - Ctrl+/ or Cmd+/   — focus the input
 *  - ArrowUp (in empty input) — edit last user message
 *  - Escape             — stop generating / blur input
 */

import { useEffect, useCallback, type RefObject } from 'react'

interface UseChatKeyboardOptions {
  inputRef: RefObject<HTMLTextAreaElement | null>
  isLoading: boolean
  onStop: () => void
  /** Called when user presses ArrowUp in empty input — receives last user message text */
  onEditLastMessage?: (text: string) => void
  /** The text of the last user message, used for ArrowUp edit */
  lastUserMessage?: string
  /** Whether shortcuts are enabled (disable when modals are open, etc.) */
  enabled?: boolean
}

export function useChatKeyboard({
  inputRef,
  isLoading,
  onStop,
  onEditLastMessage,
  lastUserMessage,
  enabled = true,
}: UseChatKeyboardOptions) {
  const handleGlobalKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return

      const isMod = e.metaKey || e.ctrlKey

      // Ctrl+/ or Cmd+/ — focus input
      if (isMod && e.key === '/') {
        e.preventDefault()
        inputRef.current?.focus()
        return
      }

      // Escape — stop generating or blur
      if (e.key === 'Escape') {
        if (isLoading) {
          e.preventDefault()
          onStop()
        } else if (document.activeElement === inputRef.current) {
          inputRef.current?.blur()
        }
        return
      }
    },
    [enabled, inputRef, isLoading, onStop],
  )

  // ArrowUp in input — edit last message
  const handleInputKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (
        e.key === 'ArrowUp' &&
        onEditLastMessage &&
        lastUserMessage &&
        inputRef.current &&
        inputRef.current.value === '' &&
        inputRef.current.selectionStart === 0
      ) {
        e.preventDefault()
        onEditLastMessage(lastUserMessage)
      }
    },
    [onEditLastMessage, lastUserMessage, inputRef],
  )

  useEffect(() => {
    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [handleGlobalKeyDown])

  return { handleInputKeyDown }
}
