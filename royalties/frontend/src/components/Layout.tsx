/** Application shell — premium SaaS layout with ambient header. */

import { useState } from 'react'
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { BookOpenCheck, LogOut, History, Upload, Shield, ChevronRight } from 'lucide-react'
import { useAuth } from '@/components/AuthContext'
import { Button } from '@/components/ui/button'
import HistorySheet from '@/components/HistorySheet'
import ThemeToggle from '@/components/ThemeToggle'
import { cn } from '@/lib/utils'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [historyOpen, setHistoryOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const isUpload = location.pathname === '/upload' || location.pathname === '/'
  const isResults = location.pathname.startsWith('/results')

  return (
    <div className="min-h-screen flex flex-col relative">
      {/* Ambient background gradient */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/[0.03] rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-primary/[0.02] rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/70 backdrop-blur-xl backdrop-saturate-150">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 h-14">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
              <BookOpenCheck className="h-4.5 w-4.5 text-primary" />
              <div className="absolute inset-0 rounded-lg ring-1 ring-primary/20 group-hover:ring-primary/40 transition-all" />
            </div>
            <div className="flex flex-col">
              <span className="font-display text-sm font-semibold tracking-tight text-foreground leading-none">
                Royalty Validator
              </span>
              <span className="text-[10px] text-muted-foreground/70 font-mono tracking-wider uppercase leading-none mt-0.5">
                Schilling ERP
              </span>
            </div>
          </Link>

          {/* Nav + Actions */}
          {user && (
            <div className="flex items-center gap-1">
              {/* Breadcrumb nav */}
              <nav className="hidden sm:flex items-center mr-4 text-xs text-muted-foreground">
                <Link
                  to="/upload"
                  className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md transition-colors',
                    isUpload
                      ? 'bg-muted text-foreground'
                      : 'hover:text-foreground hover:bg-muted/50',
                  )}
                >
                  <Upload className="h-3.5 w-3.5" />
                  Upload
                </Link>
                {isResults && (
                  <>
                    <ChevronRight className="h-3 w-3 mx-1 text-muted-foreground/40" />
                    <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-muted text-foreground">
                      <Shield className="h-3.5 w-3.5" />
                      Results
                    </span>
                  </>
                )}
              </nav>

              <Button
                variant={historyOpen ? 'secondary' : 'ghost'}
                size="sm"
                onClick={() => setHistoryOpen(!historyOpen)}
                className="gap-1.5"
              >
                <History className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">History</span>
              </Button>

              <ThemeToggle />

              <div className="h-4 w-px bg-border mx-1" />

              {/* User chip */}
              <div className="flex items-center gap-2 px-2 py-1 rounded-md">
                <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center">
                  <span className="text-[10px] font-bold text-primary uppercase">
                    {user.nickname[0]}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground font-medium hidden sm:inline max-w-[80px] truncate">
                  {user.nickname}
                </span>
              </div>

              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleLogout}
                className="text-muted-foreground hover:text-destructive"
              >
                <LogOut className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 mx-auto w-full max-w-6xl px-6 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-border/50 py-5">
        <div className="mx-auto max-w-6xl px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpenCheck className="h-3.5 w-3.5 text-muted-foreground/50" />
            <span className="text-xs text-muted-foreground/70">Royalty Statement Validator</span>
          </div>
          <span className="text-[10px] text-muted-foreground/50 font-mono">
            Schilling ERP &middot; v1.0
          </span>
        </div>
      </footer>

      {/* History sidebar */}
      <HistorySheet open={historyOpen} onOpenChange={setHistoryOpen} />
    </div>
  )
}
