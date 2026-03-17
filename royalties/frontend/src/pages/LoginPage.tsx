/** Login page — cinematic auth experience. */

import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { BookOpenCheck, ArrowRight, Shield, Zap, BarChart3 } from 'lucide-react'
import { login } from '@/api'
import { useAuth } from '@/components/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

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
    <div className="min-h-[85vh] flex">
      {/* Left — branding panel */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="hidden lg:flex flex-col justify-between w-[45%] rounded-2xl surface-elevated noise-overlay p-10 mr-8 my-4"
      >
        <div>
          <div className="flex items-center gap-3 mb-16">
            <div className="w-10 h-10 rounded-xl bg-primary/15 flex items-center justify-center">
              <BookOpenCheck className="h-5 w-5 text-primary" />
            </div>
            <span className="font-display text-lg font-semibold text-foreground">
              Royalty Validator
            </span>
          </div>

          <h2 className="font-display text-3xl font-bold text-foreground leading-tight mb-4">
            Validate settlements
            <br />
            <span className="text-gradient">with confidence.</span>
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed max-w-sm">
            Automated royalty statement validation against Schilling ERP business rules. Catch
            errors before they cost you.
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
              className="flex items-center gap-3 px-4 py-3 rounded-xl bg-background/5 border border-border/50"
            >
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <f.icon className="h-4 w-4 text-primary" />
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
        className="flex-1 flex items-center justify-center px-4"
      >
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-xl bg-primary/15 flex items-center justify-center">
              <BookOpenCheck className="h-5 w-5 text-primary" />
            </div>
            <span className="font-display text-lg font-semibold">Royalty Validator</span>
          </div>

          <div className="mb-8">
            <h1 className="font-display text-2xl font-bold text-foreground">Welcome back</h1>
            <p className="text-sm text-muted-foreground mt-1">
              Sign in to your account to continue.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label
                htmlFor="nickname"
                className="text-xs font-medium text-muted-foreground uppercase tracking-wider"
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
                className="h-11 bg-muted/30 border-border/50 focus-visible:bg-background"
              />
            </div>
            <div className="space-y-2">
              <Label
                htmlFor="password"
                className="text-xs font-medium text-muted-foreground uppercase tracking-wider"
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
                className="h-11 bg-muted/30 border-border/50 focus-visible:bg-background"
              />
            </div>

            {error && (
              <motion.p
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2"
              >
                {error}
              </motion.p>
            )}

            <Button
              type="submit"
              className="w-full h-11 font-semibold gap-2 group"
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

          <p className="mt-8 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link
              to="/register"
              className="text-primary font-semibold hover:underline underline-offset-4"
            >
              Create one
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
