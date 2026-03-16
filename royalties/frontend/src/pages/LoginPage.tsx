/** Login page — simple nickname-based identification. */

import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpenCheck } from 'lucide-react';
import { identify } from '../api';
import { Button, Input, Card } from '../components/ui';

export default function LoginPage() {
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!nickname.trim()) return;
    setLoading(true);
    setError('');
    try {
      const user = await identify(nickname.trim());
      localStorage.setItem('rsv_user_id', user.user_id);
      localStorage.setItem('rsv_nickname', user.nickname);
      navigate('/upload');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to identify');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-[70vh] items-center justify-center">
      <Card className="w-full max-w-md p-8">
        <div className="flex flex-col items-center gap-4 mb-8">
          <div className="rounded-full bg-brand-100 p-4">
            <BookOpenCheck className="h-8 w-8 text-brand-700" />
          </div>
          <h1 className="font-display text-2xl text-ink-900">
            Royalty Statement Validator
          </h1>
          <p className="text-sm text-ink-500 text-center max-w-xs">
            Validate royalty settlement files against Schilling ERP business
            rules. Enter a nickname to get started.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            placeholder="Your nickname"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            maxLength={100}
            autoFocus
          />
          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}
          <Button type="submit" className="w-full" disabled={loading || !nickname.trim()}>
            {loading ? 'Signing in…' : 'Continue'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
