/** Application shell — premium SaaS layout with ambient header. */

import { useState } from 'react'
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'motion/react'
import {
  BookOpenCheck,
  LogOut,
  History,
  Upload,
  Shield,
  ChevronRight,
  Bot,
  Menu,
  X,
} from 'lucide-react'
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  function handleLogout() {
    logout()
    navigate('/login')
  }

  const isUpload = location.pathname === '/upload' || location.pathname === '/'
  const isResults = location.pathname.startsWith('/results')
  const isHelp = location.pathname === '/help'
  const isFullWidth = isResults // Results page needs full width for the document panel

  return (
    <div className="h-dvh flex flex-col relative overflow-hidden">
      {/* Ambient background gradient */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-primary/[0.03] rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-primary/[0.02] rounded-full blur-[100px]" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/70 backdrop-blur-xl backdrop-saturate-150">
        <div className="flex items-center h-14 px-4 sm:px-6">
          {/* Left — Logo */}
          <Link to="/" className="flex items-center gap-3 group shrink-0">
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

          {user && (
            <>
              {/* Center — Navigation */}
              <nav className="hidden sm:flex items-center gap-1 mx-auto text-sm text-muted-foreground">
                <Link
                  to="/upload"
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors',
                    isUpload
                      ? 'bg-muted text-foreground font-medium'
                      : 'hover:text-foreground hover:bg-muted/50',
                  )}
                >
                  <Upload className="h-3.5 w-3.5" />
                  Upload
                </Link>
                {isResults && (
                  <>
                    <ChevronRight className="h-3 w-3 text-muted-foreground/40" />
                    <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-muted text-foreground font-medium">
                      <Shield className="h-3.5 w-3.5" />
                      Results
                    </span>
                  </>
                )}
                <Link
                  to="/help"
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-colors',
                    isHelp
                      ? 'bg-muted text-foreground font-medium'
                      : 'hover:text-foreground hover:bg-muted/50',
                  )}
                >
                  <Bot className="h-3.5 w-3.5" />
                  Help
                </Link>
              </nav>

              {/* Mobile menu toggle */}
              <div className="flex-1 sm:hidden" />
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="sm:hidden text-muted-foreground"
              >
                {mobileMenuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </Button>

              {/* Right — Actions */}
              <div className="hidden sm:flex items-center gap-1 shrink-0">
                <Button
                  variant={historyOpen ? 'secondary' : 'ghost'}
                  size="sm"
                  onClick={() => setHistoryOpen(!historyOpen)}
                  className="gap-1.5"
                >
                  <History className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">History</span>
                </Button>

                <div className="h-4 w-px bg-border mx-1" />

                {/* User chip */}
                <div className="flex items-center gap-2 px-2 py-1 rounded-md">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center">
                    <span className="text-[10px] font-bold text-primary uppercase">
                      {user.nickname[0]}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground font-medium max-w-[80px] truncate">
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

                <ThemeToggle />
              </div>
            </>
          )}
          {!user && <div className="flex-1" />}
          {!user && <ThemeToggle />}
        </div>
      </header>

      {/* Mobile menu dropdown */}
      <AnimatePresence>
        {mobileMenuOpen && user && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="sm:hidden border-b border-border/50 bg-background/95 backdrop-blur-xl overflow-hidden z-40"
          >
            <nav className="flex flex-col px-4 py-2 gap-1">
              <Link
                to="/upload"
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2.5 rounded-md text-sm transition-colors',
                  isUpload
                    ? 'bg-muted text-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
                )}
              >
                <Upload className="h-4 w-4" />
                Upload
              </Link>
              <Link
                to="/help"
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2.5 rounded-md text-sm transition-colors',
                  isHelp
                    ? 'bg-muted text-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
                )}
              >
                <Bot className="h-4 w-4" />
                Help
              </Link>
              <button
                onClick={() => {
                  setHistoryOpen(true)
                  setMobileMenuOpen(false)
                }}
                className="flex items-center gap-2 px-3 py-2.5 rounded-md text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors text-left"
              >
                <History className="h-4 w-4" />
                History
              </button>
            </nav>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content */}
      <main
        className={cn(
          'flex-1 min-h-0 w-full flex flex-col',
          isFullWidth
            ? 'max-w-full px-4 sm:px-6 pt-3 pb-1 overflow-hidden'
            : 'mx-auto max-w-6xl px-4 sm:px-6 pt-3 pb-3 overflow-y-auto',
        )}
      >
        <Outlet />
      </main>

      {/* Footer — hidden on full-width pages to maximise vertical space */}
      {!isFullWidth && (
        <footer className="border-t border-border/50 py-3 shrink-0">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpenCheck className="h-3.5 w-3.5 text-muted-foreground/50" />
              <span className="text-xs text-muted-foreground/70">Royalty Statement Validator</span>
            </div>
            <span className="text-[10px] text-muted-foreground/50 font-mono">
              Schilling ERP &middot; v1.0
            </span>
          </div>
        </footer>
      )}

      {/* History sidebar */}
      <HistorySheet open={historyOpen} onOpenChange={setHistoryOpen} />
    </div>
  )
}
