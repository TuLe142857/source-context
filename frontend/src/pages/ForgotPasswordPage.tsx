import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Send } from 'lucide-react';
import { AuthLayout } from '@/components/AuthLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TemplateBadge } from '@/components/TemplateBadge';
import { useForgotPasswordMutation } from '@/hooks/useAccount';
import { getErrorMessage } from '@/lib/errors';

export function ForgotPasswordPage() {
  const mutation = useForgotPasswordMutation();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate(
      { email },
      {
        onSuccess: () => setSent(true),
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <AuthLayout title="Quên mật khẩu" subtitle="Yêu cầu liên kết đặt lại mật khẩu qua email">
      <div className="mb-4">
        <TemplateBadge label="Backend chưa hỗ trợ" />
      </div>
      {sent ? (
        <p className="text-sm text-muted-foreground">
          Nếu email tồn tại, một liên kết đặt lại mật khẩu sẽ được gửi tới bạn.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="forgot-email">Email</Label>
            <Input
              id="forgot-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
          </div>
          <Button type="submit" className="w-full" disabled={mutation.isPending}>
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Gửi liên kết đặt lại
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
