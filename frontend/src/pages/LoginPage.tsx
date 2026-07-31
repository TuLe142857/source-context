import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2 } from 'lucide-react';
import { AuthLayout } from '@/components/AuthLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useLoginMutation } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';

export function LoginPage() {
  const navigate = useNavigate();
  const loginMutation = useLoginMutation();
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    loginMutation.mutate(
      { username_or_email: usernameOrEmail, password },
      { onSuccess: () => navigate('/workspaces', { replace: true }) }
    );
  };

  return (
    <AuthLayout
      title="Đăng nhập"
      subtitle="Hệ thống quản lý workspace & mã nguồn thông minh"
      footer="Powered by SourceContext"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {loginMutation.isError && (
          <p className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-xl p-3">
            {getErrorMessage(loginMutation.error)}
          </p>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="username_or_email">Username hoặc Email</Label>
          <Input
            id="username_or_email"
            required
            value={usernameOrEmail}
            onChange={(e) => setUsernameOrEmail(e.target.value)}
            placeholder="username hoặc you@example.com"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Mật khẩu</Label>
          <Input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          <div className="text-right">
            <Link to="/forgot-password" className="text-xs text-muted-foreground hover:text-primary">
              Quên mật khẩu?
            </Link>
          </div>
        </div>

        <Button type="submit" className="w-full" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              Đăng nhập <ArrowRight className="w-4 h-4" />
            </>
          )}
        </Button>
      </form>

      <p className="text-center text-xs text-muted-foreground mt-6">
        Chưa có tài khoản?{' '}
        <Link to="/register" className="text-primary font-medium hover:underline">
          Đăng ký ngay
        </Link>
      </p>
    </AuthLayout>
  );
}
