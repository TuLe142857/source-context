import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Loader2 } from 'lucide-react';
import { AuthLayout } from '@/components/AuthLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useRegisterMutation } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';

export function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegisterMutation();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    registerMutation.mutate(
      { email, username, password, full_name: fullName || undefined },
      { onSuccess: () => navigate('/workspaces', { replace: true }) }
    );
  };

  return (
    <AuthLayout
      title="Tạo tài khoản mới"
      subtitle="Hệ thống quản lý workspace & mã nguồn thông minh"
      footer="Powered by SourceContext"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {registerMutation.isError && (
          <p className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-xl p-3">
            {getErrorMessage(registerMutation.error)}
          </p>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="full_name">Họ và tên</Label>
          <Input
            id="full_name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Nguyễn Văn A"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email">Email *</Label>
          <Input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="username">Username *</Label>
          <Input
            id="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="username"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password">Mật khẩu *</Label>
          <Input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
        </div>

        <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              Tạo tài khoản <ArrowRight className="w-4 h-4" />
            </>
          )}
        </Button>
      </form>

      <p className="text-center text-xs text-muted-foreground mt-6">
        Đã có tài khoản?{' '}
        <Link to="/login" className="text-primary font-medium hover:underline">
          Đăng nhập
        </Link>
      </p>
    </AuthLayout>
  );
}
