import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { Loader2, UserCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TemplateBadge } from '@/components/TemplateBadge';
import { useSession } from '@/hooks/useAuth';
import { useUpdateProfileMutation } from '@/hooks/useAccount';
import { getErrorMessage } from '@/lib/errors';

export function ProfilePage() {
  const { user } = useSession();
  const updateMutation = useUpdateProfileMutation();

  const [username, setUsername] = useState(user?.username ?? '');
  const [fullName, setFullName] = useState(user?.full_name ?? '');
  const [email, setEmail] = useState(user?.email ?? '');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(
      { username, full_name: fullName, email },
      {
        onSuccess: () => toast.success('Đã cập nhật hồ sơ.'),
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <div className="max-w-lg space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <UserCircle className="w-6 h-6 text-primary" /> Hồ sơ cá nhân <TemplateBadge />
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Backend chưa có endpoint cập nhật hồ sơ — form dưới đây là giao diện chuẩn bị trước.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="glass-card rounded-2xl border p-6 space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="profile-username">Username</Label>
          <Input id="profile-username" value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="profile-fullname">Họ và tên</Label>
          <Input id="profile-fullname" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="profile-email">Email</Label>
          <Input id="profile-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <Button type="submit" disabled={updateMutation.isPending}>
          {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Lưu thay đổi'}
        </Button>
      </form>
    </div>
  );
}
