import { Navigate, Outlet } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useCurrentUserQuery, useSession } from '@/hooks/useAuth';

/** Gates authenticated routes: no token -> /login; token present -> validate via /auth/me. */
export function ProtectedRoute() {
  const { token } = useSession();
  const { isLoading } = useCurrentUserQuery();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return <Outlet />;
}
