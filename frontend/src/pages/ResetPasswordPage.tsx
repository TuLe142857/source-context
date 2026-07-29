import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { KeyRound, Loader2 } from 'lucide-react';
import { AuthLayout } from '@/components/AuthLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TemplateBadge } from '@/components/TemplateBadge';
import { useResetPasswordMutation } from '@/hooks/useAccount';
import { getErrorMessage } from '@/lib/errors';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const mutation = useResetPasswordMutation();
  const [newPassword, setNewPassword] = useState('');
  const [done, setDone] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate(
      { token, new_password: newPassword },
      {
        onSuccess: () => setDone(true),
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <AuthLayout title="Đặt lại mật khẩu" subtitle="Nhập mật khẩu mới cho tài khoản của bạn">
      <div className="mb-4">
        <TemplateBadge label="Backend chưa hỗ trợ" />
      </div>
      {done ? (
        <p className="text-sm text-muted-foreground">
          Mật khẩu đã được đặt lại. Bạn có thể đăng nhập bằng mật khẩu mới.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="reset-password">Mật khẩu mới</Label>
            <Input
              id="reset-password"
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <KeyRound className="w-4 h-4" />}
            Đặt lại mật khẩu
          </Button>
        </form>
      )}
      <p className="text-center text-xs text-muted-foreground mt-6">
        <Link to="/login" className="text-primary font-medium hover:underline">
          Quay lại đăng nhập
        </Link>
      </p>
    </AuthLayout>
  );
}
