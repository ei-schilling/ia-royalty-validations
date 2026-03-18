/** Route guard — redirects unauthenticated users to login. */

import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/components/AuthContext'
import { Spinner } from '@/components/ui/spinner'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="h-8 w-8" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}
