/** Login page — authenticate with nickname + password. */

import { useState, type FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { BookOpenCheck } from 'lucide-react'
import { login } from '@/api'
import { useAuth } from '@/components/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'

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
    <div className="flex min-h-[70vh] items-center justify-center">
      <Card className="w-full max-w-md p-8">
        <div className="flex flex-col items-center gap-4 mb-8">
          <div className="rounded-full bg-brand-100 p-4">
            <BookOpenCheck className="h-8 w-8 text-brand-700" />
          </div>
          <h1 className="font-display text-2xl text-ink-900">Royalty Statement Validator</h1>
          <p className="text-sm text-ink-500 text-center max-w-xs">
            Validate royalty settlement files against Schilling ERP business rules.
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
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button
            type="submit"
            className="w-full"
            disabled={loading || !nickname.trim() || !password}
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-500">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="text-brand-600 font-medium hover:underline">
            Create one
          </Link>
        </p>
      </Card>
    </div>
  )
}
