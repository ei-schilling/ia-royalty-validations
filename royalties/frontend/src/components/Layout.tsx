/** Application shell with header and navigation. */

import { Outlet, Link } from 'react-router-dom';
import { BookOpenCheck } from 'lucide-react';

export default function Layout() {
  const nickname = localStorage.getItem('rsv_nickname');

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-ink-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="mx-auto max-w-5xl flex items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2.5 group">
            <BookOpenCheck className="h-6 w-6 text-brand-600 group-hover:text-brand-700 transition-colors" />
            <span className="font-display text-lg text-ink-900">
              Royalty Validator
            </span>
          </Link>
          {nickname && (
            <span className="text-xs text-ink-400 font-mono">{nickname}</span>
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
  );
}
