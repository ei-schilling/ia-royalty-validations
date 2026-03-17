/** Shared UI components for the Royalty Statement Validator. */

import { type ReactNode } from 'react'
import { cn } from '../lib/utils'

/* ─── Card ───────────────────────────────────────────────────────── */

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('rounded-xl border border-ink-200 bg-white shadow-sm', className)}>
      {children}
    </div>
  )
}

/* ─── Button ─────────────────────────────────────────────────────── */

type ButtonVariant = 'primary' | 'secondary' | 'ghost'

const buttonStyles: Record<ButtonVariant, string> = {
  primary: 'bg-brand-700 text-white hover:bg-brand-800 active:bg-brand-900 shadow-sm',
  secondary: 'bg-white border border-ink-300 text-ink-800 hover:bg-ink-50 active:bg-ink-100',
  ghost: 'text-ink-600 hover:bg-ink-100 active:bg-ink-200',
}

export function Button({
  children,
  variant = 'primary',
  className,
  disabled,
  ...rest
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none',
        buttonStyles[variant],
        className,
      )}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  )
}

/* ─── Badge ──────────────────────────────────────────────────────── */

const badgeColors = {
  error: 'bg-red-100 text-red-800 border-red-200',
  warning: 'bg-amber-100 text-amber-800 border-amber-200',
  info: 'bg-sky-100 text-sky-800 border-sky-200',
  success: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  neutral: 'bg-ink-100 text-ink-700 border-ink-200',
}

export function Badge({
  children,
  color = 'neutral',
}: {
  children: ReactNode
  color?: keyof typeof badgeColors
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        badgeColors[color],
      )}
    >
      {children}
    </span>
  )
}

/* ─── Spinner ────────────────────────────────────────────────────── */

export function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={cn('animate-spin h-5 w-5 text-brand-600', className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  )
}

/* ─── Input ──────────────────────────────────────────────────────── */

export function Input({ className, ...rest }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'w-full rounded-lg border border-ink-300 bg-white px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 transition-colors',
        className,
      )}
      {...rest}
    />
  )
}
