import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, ArrowRight, Loader2 } from 'lucide-react';
import { AuthLayout } from '@/components/AuthLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useRegisterRequestOtpMutation, useRegisterVerifyOtpMutation } from '@/hooks/useAuth';
import { getErrorMessage } from '@/lib/errors';

export function RegisterPage() {
  const navigate = useNavigate();
  const requestOtpMutation = useRegisterRequestOtpMutation();
  const verifyOtpMutation = useRegisterVerifyOtpMutation();

  const [step, setStep] = useState<'email' | 'verify'>('email');
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');

  const handleSendOtp = (e: FormEvent) => {
    e.preventDefault();
    requestOtpMutation.mutate(
      { email },
      { onSuccess: () => setStep('verify') }
    );
  };

  const handleResendOtp = () => {
    requestOtpMutation.mutate(
      { email },
      { onSuccess: () => toast.success('Đã gửi lại mã OTP tới email của bạn.') }
    );
  };

  const handleBackToEmail = () => {
    setStep('email');
    setOtp('');
  };

  const handleVerify = (e: FormEvent) => {
    e.preventDefault();
    verifyOtpMutation.mutate(
      { email, username, password, full_name: fullName || undefined, otp },
      { onSuccess: () => navigate('/workspaces', { replace: true }) }
    );
  };

  if (step === 'email') {
    return (
      <AuthLayout
        title="Tạo tài khoản mới"
        subtitle="Hệ thống quản lý workspace & mã nguồn thông minh"
        footer="Powered by SourceContext"
      >
        <form onSubmit={handleSendOtp} className="space-y-4">
          {requestOtpMutation.isError && (
            <p className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-xl p-3">
              {getErrorMessage(requestOtpMutation.error)}
            </p>
          )}

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

          <Button type="submit" className="w-full" disabled={requestOtpMutation.isPending}>
            {requestOtpMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                Gửi mã OTP <ArrowRight className="w-4 h-4" />
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

  return (
    <AuthLayout
      title="Xác thực email"
      subtitle="Hệ thống quản lý workspace & mã nguồn thông minh"
      footer="Powered by SourceContext"
    >
      <form onSubmit={handleVerify} className="space-y-4">
        <p className="text-xs text-muted-foreground -mt-2">
          Mã OTP đã được gửi tới <span className="font-medium text-foreground">{email}</span>. Mã có hiệu lực
          trong 5 phút.
        </p>

        {verifyOtpMutation.isError && (
          <p className="text-xs text-destructive bg-destructive/10 border border-destructive/30 rounded-xl p-3">
            {getErrorMessage(verifyOtpMutation.error)}
          </p>
        )}

        <div className="space-y-1.5">
          <Label htmlFor="otp">Mã OTP *</Label>
          <Input
            id="otp"
            required
            inputMode="numeric"
            autoComplete="one-time-code"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            placeholder="Nhập mã 6 số"
          />
        </div>

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

        <Button type="submit" className="w-full" disabled={verifyOtpMutation.isPending}>
          {verifyOtpMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              Hoàn tất đăng ký <ArrowRight className="w-4 h-4" />
            </>
          )}
        </Button>

        <div className="flex items-center justify-between text-xs">
          <button
            type="button"
            onClick={handleBackToEmail}
            className="flex items-center gap-1 text-muted-foreground hover:text-primary"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Đổi email
          </button>
          <button
            type="button"
            onClick={handleResendOtp}
            disabled={requestOtpMutation.isPending}
            className="text-primary font-medium hover:underline disabled:opacity-50"
          >
            Gửi lại mã OTP
          </button>
        </div>
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
