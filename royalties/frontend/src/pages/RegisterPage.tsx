/** Register page — create a new user account. */

import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { ArrowRight, UserPlus } from 'lucide-react'
import { register } from '@/api'
import { useAuth } from '@/components/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import AuthBackground from '@/components/AuthBackground'

export default function RegisterPage() {
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { setAuth } = useAuth()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!nickname.trim() || !password) return
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    if (password.length < 4) {
      setError('Password must be at least 4 characters')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await register(nickname.trim(), password)
      setAuth(res.access_token, res.user)
      navigate('/upload')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const strength = password.length === 0 ? 0 : password.length < 4 ? 1 : password.length < 8 ? 2 : 3
  const strengthLabel = ['', 'Weak', 'Fair', 'Strong'][strength]
  const strengthColor = ['', 'bg-destructive', 'bg-amber-500', 'bg-emerald-500'][strength]

  return (
    <div className="min-h-[85vh] flex items-center justify-center px-4 relative">
      <AuthBackground />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-sm"
      >
        <div className="flex items-center gap-3 mb-10">
          <div className="w-10 h-10 rounded-xl bg-primary/15 flex items-center justify-center">
            <UserPlus className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="font-display text-xl font-bold text-foreground">Create Account</h1>
            <p className="text-xs text-muted-foreground">Get started with Royalty Validator</p>
          </div>
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
              placeholder="Choose a nickname"
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
              className="text-xs font-medium text-muted-foreground uppercase tracking-wider"
            >
              Password
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="Create a password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              maxLength={128}
              className="h-11 border-border/50"
            />
            {password.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className="flex items-center gap-2 pt-1"
              >
                <div className="flex gap-1 flex-1">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
                        i <= strength ? strengthColor : 'bg-border'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-[10px] text-muted-foreground font-mono">{strengthLabel}</span>
              </motion.div>
            )}
          </div>
          <div className="space-y-2">
            <Label
              htmlFor="confirm"
              className="text-xs font-medium text-muted-foreground uppercase tracking-wider"
            >
              Confirm password
            </Label>
            <Input
              id="confirm"
              type="password"
              placeholder="Confirm your password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
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
            disabled={loading || !nickname.trim() || !password || !confirm}
          >
            {loading ? (
              'Creating account…'
            ) : (
              <>
                Create Account
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </>
            )}
          </Button>
        </form>

        <p className="mt-8 text-center text-sm text-muted-foreground">
          Already have an account?{' '}
          <Link
            to="/login"
            className="text-primary font-semibold hover:underline underline-offset-4"
          >
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  )
}
