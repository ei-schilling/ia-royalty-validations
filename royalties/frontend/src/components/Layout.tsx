/** Application shell with header and navigation. */

import { Outlet, Link, useNavigate } from 'react-router-dom'
import { BookOpenCheck, LogOut } from 'lucide-react'
import { useAuth } from '@/components/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-ink-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto max-w-5xl flex items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2.5 group">
            <BookOpenCheck className="h-6 w-6 text-brand-600 group-hover:text-brand-700 transition-colors" />
            <span className="font-display text-lg text-ink-900">Royalty Validator</span>
          </Link>
          {user && (
            <div className="flex items-center gap-3">
              <span className="text-xs text-ink-400 font-mono">{user.nickname}</span>
              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 text-xs text-ink-500 hover:text-ink-700 transition-colors"
              >
                <LogOut className="h-3.5 w-3.5" />
                Logout
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-ink-100 py-4 text-center text-xs text-ink-400">
        Royalty Statement Validator &middot; Schilling ERP
      </footer>
    </div>
  )
}
