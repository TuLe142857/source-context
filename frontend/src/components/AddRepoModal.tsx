import React, { useState } from 'react';
import { X, GitBranch, Link, FileText, Info } from 'lucide-react';

interface AddRepoModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (data: {
    name: string;
    git_url: string;
    description?: string;
    default_branch?: string;
  }) => Promise<void>;
}

export const AddRepoModal: React.FC<AddRepoModalProps> = ({
  isOpen,
  onClose,
  onAdd,
}) => {
  const [name, setName] = useState<string>('');
  const [gitUrl, setGitUrl] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [defaultBranch, setDefaultBranch] = useState<string>('main');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !gitUrl.trim()) {
      setError('Vui lòng nhập tên repository và URL Git hợp lệ.');
      return;
    }
    setError(null);
    setIsSubmitting(true);

    try {
      await onAdd({
        name: name.trim(),
        git_url: gitUrl.trim(),
        description: description.trim() || undefined,
        default_branch: defaultBranch.trim() || 'main',
      });
      setName('');
      setGitUrl('');
      setDescription('');
      setDefaultBranch('main');
      onClose();
    } catch (err: any) {
      setError(err.message || 'Không thể liên kết Git repository.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg glass-panel rounded-3xl p-6 sm:p-8 border border-white/10 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 rounded-2xl bg-cyan-600/20 border border-cyan-500/30 text-cyan-400">
            <GitBranch className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Thêm Git Repository</h2>
            <p className="text-xs text-gray-400">Đính kèm link kho chứa mã nguồn vào project</p>
          </div>
        </div>

        <div className="mb-5 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs flex items-start gap-2">
          <Info className="w-4 h-4 shrink-0 mt-0.5" />
          <span>
            Repository khi thêm mới sẽ ở trạng thái <strong>pending</strong> (chưa chạy indexing tự động).
          </span>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1.5">
              Tên gợi nhớ Repository <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <FileText className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="text"
                required
                placeholder="ví dụ: backend-service"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-10 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1.5">
              Đường dẫn Git (Git Clone URL) <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <Link className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
              <input
                type="url"
                required
                placeholder="https://github.com/organization/repo.git"
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-10 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all font-mono text-xs"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                Default Branch
              </label>
              <div className="relative">
                <GitBranch className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-500" />
                <input
                  type="text"
                  placeholder="main"
                  value={defaultBranch}
                  onChange={(e) => setDefaultBranch(e.target.value)}
                  className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-10 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                Mô tả
              </label>
              <input
                type="text"
                placeholder="Kho lưu trữ mã nguồn..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-950/60 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
              />
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
              className="bg-cyan-600 hover:bg-cyan-500 text-white px-5 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer disabled:opacity-50 transition-colors shadow-lg shadow-cyan-600/30"
            >
              {isSubmitting ? (
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <span>Thêm Repo</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
