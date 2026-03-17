/** Register page — create a new user account. */

import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { register } from '@/api'
import { useAuth } from '@/components/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'

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

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <Card className="w-full max-w-md p-8">
        <div className="flex flex-col items-center gap-4 mb-8">
          <div className="rounded-full bg-brand-100 p-4">
            <UserPlus className="h-8 w-8 text-brand-700" />
          </div>
          <h1 className="font-display text-2xl text-ink-900">Create Account</h1>
          <p className="text-sm text-ink-500 text-center max-w-xs">
            Create a new account to start validating royalty statements.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Nickname"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            maxLength={100}
            autoFocus
          />
          <Input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            maxLength={128}
          />
          <Input
            type="password"
            placeholder="Confirm password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            maxLength={128}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button
            type="submit"
            className="w-full"
            disabled={loading || !nickname.trim() || !password || !confirm}
          >
            {loading ? 'Creating account…' : 'Create Account'}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-500">
          Already have an account?{' '}
          <Link to="/login" className="text-brand-600 font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  )
}
