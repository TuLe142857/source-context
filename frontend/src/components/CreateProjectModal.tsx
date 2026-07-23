import React, { useState } from 'react';
import { X, FolderPlus, Sparkles } from 'lucide-react';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (name: string, description?: string) => Promise<void>;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  isOpen,
  onClose,
  onCreate,
}) => {
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Vui lòng nhập tên project.');
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      await onCreate(name.trim(), description.trim() || undefined);
      setName('');
      setDescription('');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Không thể tạo project');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg glass-panel rounded-3xl p-6 sm:p-8 border border-white/10 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400">
            <FolderPlus className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Tạo Project Mới</h2>
            <p className="text-xs text-gray-400">Khởi tạo workspace quản lý repos & team members</p>
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
              Tên Project <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="ví dụ: E-Commerce Microservices"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1.5">
              Mô tả ngắn
            </label>
            <textarea
              rows={3}
              placeholder="Dự án bao gồm backend FastAPI, frontend React và crawler dịch vụ..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-white/10">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 text-xs font-medium transition-colors"
            >
              Hủy bỏ
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="gradient-btn text-white px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Xác nhận tạo</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
