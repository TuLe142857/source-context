import React, { useState } from 'react';
import { X, UserPlus, Mail, Shield } from 'lucide-react';
import type { MemberRole } from '../types';

interface InviteMemberModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInvite: (email: string, role: MemberRole) => Promise<void>;
}

export const InviteMemberModal: React.FC<InviteMemberModalProps> = ({
  isOpen,
  onClose,
  onInvite,
}) => {
  const [email, setEmail] = useState<string>('');
  const [role, setRole] = useState<MemberRole>('Viewer');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) {
      setError('Vui lòng nhập địa chỉ email.');
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      await onInvite(email.trim(), role);
      setEmail('');
      setRole('Viewer');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Không thể gửi lời mời thành viên.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-md glass-panel rounded-3xl p-6 sm:p-8 border border-white/10 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-2xl bg-purple-600/20 border border-purple-500/30 text-purple-400">
            <UserPlus className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Mời Thành Viên</h2>
            <p className="text-xs text-gray-400">Gửi lời mời tham gia project qua email</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1.5">
              Email thành viên <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="email"
                required
                placeholder="colleague@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-10 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1.5">
              Phân quyền (Role)
            </label>
            <div className="relative">
              <Shield className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as MemberRole)}
                className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-10 py-2.5 text-sm text-white focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all appearance-none cursor-pointer"
              >
                <option value="Admin" className="bg-slate-900 text-white">Admin (Toàn quyền quản trị)</option>
                <option value="Developer" className="bg-slate-900 text-white">Developer (Thêm/Sửa Repos & Code)</option>
                <option value="Viewer" className="bg-slate-900 text-white">Viewer (Chỉ xem và truy vấn)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 text-xs font-medium transition-colors"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="bg-purple-600 hover:bg-purple-500 text-white px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer disabled:opacity-50 transition-colors shadow-lg shadow-purple-600/30"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <span>Gửi lời mời</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
