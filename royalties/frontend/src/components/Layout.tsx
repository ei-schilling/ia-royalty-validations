/** Application shell with header and navigation. */

import { useState } from 'react'
import { Outlet, Link, useNavigate } from 'react-router-dom'
import { BookOpenCheck, LogOut, History } from 'lucide-react'
import { useAuth } from '@/components/AuthContext'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import HistorySheet from '@/components/HistorySheet'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [historyOpen, setHistoryOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto max-w-5xl flex items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2.5 group">
            <BookOpenCheck className="h-6 w-6 text-primary group-hover:text-primary/80 transition-colors" />
            <span className="font-display text-lg text-foreground">Royalty Validator</span>
          </Link>
          {user && (
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={() => setHistoryOpen(true)}>
                <History className="h-3.5 w-3.5" />
                History
              </Button>
              <Separator orientation="vertical" className="h-4" />
              <span className="text-xs text-muted-foreground font-mono">{user.nickname}</span>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="h-3.5 w-3.5" />
                Logout
              </Button>
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 mx-auto w-full max-w-5xl px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-4 text-center text-xs text-muted-foreground">
        Royalty Statement Validator &middot; Schilling ERP
      </footer>

      {/* History sidebar */}
      <HistorySheet open={historyOpen} onOpenChange={setHistoryOpen} />
    </div>
  )
}
