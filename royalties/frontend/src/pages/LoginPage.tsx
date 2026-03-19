/** Login page — cinematic auth experience. */

import { login } from '@/api'
import AuthBackground from '@/components/AuthBackground'
import { useAuth } from '@/components/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowRight, BarChart3, BookOpenCheck, Shield, Zap } from 'lucide-react'
import { motion } from 'motion/react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

export default function LoginPage() {
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { setAuth } = useAuth()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!nickname.trim() || !password) return
    setLoading(true)
    setError('')
    try {
      const res = await login(nickname.trim(), password)
      setAuth(res.access_token, res.user)
      navigate('/upload')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to login')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex relative">
      <AuthBackground />
      {/* Left — branding panel */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="hidden lg:flex flex-col justify-between w-[45%] rounded-2xl surface-elevated noise-overlay p-10 mr-8 my-4"
      >
        <div className="flex flex-col justify-between">
          <div className="flex gap-3 items-center mb-16">
            <div className="flex justify-center items-center w-10 h-10 rounded-xl bg-primary/15">
              <BookOpenCheck className="w-5 h-5 text-primary" />
            </div>
            <span className="text-lg font-semibold font-display text-foreground">
              Royalty Validator
            </span>
          </div>

          <h2 className="mb-4 text-3xl font-bold leading-tight font-display text-foreground">
            Every royalty,
            <br />
            every row —
            <br />
            <span className="text-gradient">verified in seconds.</span>
          </h2>
          <p className="max-w-sm text-sm leading-relaxed text-muted-foreground">
            Stop chasing discrepancies across spreadsheets. Upload your settlement files, and let
            the engine cross-check rates, territories, deductions, and totals against Schilling ERP
            — automatically. When something doesn&apos;t add up, you&apos;ll know exactly where and
            why.
          </p>
        </div>

        {/* Feature pills */}
        <div className="space-y-3">
          {[
            { icon: Shield, text: '17 validation rules', sub: 'Comprehensive checks' },
            { icon: Zap, text: 'Instant analysis', sub: 'Results in seconds' },
            { icon: BarChart3, text: 'Detailed reports', sub: 'Row-level diagnostics' },
          ].map((f, i) => (
            <motion.div
              key={f.text}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.1, duration: 0.4 }}
              className="flex gap-3 items-center px-4 py-3 rounded-xl border bg-background/5 border-border/50"
            >
              <div className="flex justify-center items-center w-8 h-8 rounded-lg bg-primary/10 shrink-0">
                <f.icon className="w-4 h-4 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">{f.text}</p>
                <p className="text-xs text-muted-foreground">{f.sub}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {/* Right — form */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="flex flex-1 justify-center items-center px-4"
      >
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex gap-3 items-center mb-10 lg:hidden">
            <div className="flex justify-center items-center w-10 h-10 rounded-xl bg-primary/15">
              <BookOpenCheck className="w-5 h-5 text-primary" />
            </div>
            <span className="text-lg font-semibold font-display">Royalty Validator</span>
          </div>

          <div className="mb-8">
            <h1 className="text-2xl font-bold font-display text-foreground">Welcome back</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Sign in to your account to continue.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label
                htmlFor="nickname"
                className="text-xs font-medium tracking-wider uppercase text-muted-foreground"
              >
                Nickname
              </Label>
              <Input
                id="nickname"
                placeholder="Enter your nickname"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                maxLength={100}
                autoFocus
                className="h-11 border-border/50"
              />
            </div>
            <div className="space-y-2">
              <Label
                htmlFor="password"
                className="text-xs font-medium tracking-wider uppercase text-muted-foreground"
              >
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                maxLength={128}
                className="h-11 border-border/50"
              />
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="px-3 py-2 text-sm rounded-lg border text-destructive bg-destructive/10 border-destructive/20"
              >
                {error}
              </motion.p>
            )}

            <Button
              type="submit"
              className="gap-2 w-full h-11 font-semibold group"
              disabled={loading || !nickname.trim() || !password}
            >
              {loading ? (
                'Signing in…'
              ) : (
                <>
                  Sign In
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </>
              )}
            </Button>
          </form>

          <p className="mt-8 text-sm text-center text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link
              to="/register"
              className="font-semibold text-primary hover:underline underline-offset-4"
            >
              Create one
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
