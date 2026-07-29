import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { Loader2, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TemplateBadge } from '@/components/TemplateBadge';
import { useChangePasswordMutation } from '@/hooks/useAccount';
import { getErrorMessage } from '@/lib/errors';

export function SecurityPage() {
  const changePasswordMutation = useChangePasswordMutation();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('Mật khẩu mới không khớp.');
      return;
    }
    changePasswordMutation.mutate(
      { current_password: currentPassword, new_password: newPassword },
      {
        onSuccess: () => toast.success('Đã đổi mật khẩu.'),
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-primary" /> Bảo mật <TemplateBadge />
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Backend chưa có endpoint đổi mật khẩu — form dưới đây là giao diện chuẩn bị trước.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card rounded-2xl border p-6 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="current-password">Mật khẩu hiện tại</Label>
          <Input
            id="current-password"
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="new-password">Mật khẩu mới</Label>
          <Input
            id="new-password"
            type="password"
            required
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="confirm-password">Xác nhận mật khẩu mới</Label>
          <Input
            id="confirm-password"
            type="password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
        </div>
        <Button type="submit" disabled={changePasswordMutation.isPending}>
          {changePasswordMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Đổi mật khẩu'}
        </Button>
      </form>
    </div>
  );
}
