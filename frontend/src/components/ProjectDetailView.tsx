import React, { useState } from 'react';
import type { ProjectDetail, MemberRole } from '../types';
import {
  ArrowLeft,
  Users,
  GitBranch,
  UserPlus,
  Plus,
  Trash2,
  ExternalLink,
  Shield,
  Clock,
} from 'lucide-react';

interface ProjectDetailViewProps {
  project: ProjectDetail;
  isLoading: boolean;
  onBack: () => void;
  onOpenInviteModal: () => void;
  onOpenAddRepoModal: () => void;
  onRemoveMember: (userId: number) => Promise<void>;
}

export const ProjectDetailView: React.FC<ProjectDetailViewProps> = ({
  project,
  isLoading,
  onBack,
  onOpenInviteModal,
  onOpenAddRepoModal,
  onRemoveMember,
}) => {
  const [activeTab, setActiveTab] = useState<'repos' | 'members'>('repos');
  const [removingId, setRemovingId] = useState<number | null>(null);

  const handleRemove = async (userId: number) => {
    if (!window.confirm('Bạn có chắc chắn muốn xóa thành viên này khỏi project?')) return;
    setRemovingId(userId);
    try {
      await onRemoveMember(userId);
    } finally {
      setRemovingId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-pulse">
        <div className="h-8 bg-slate-800 rounded-lg w-48 mb-6"></div>
        <div className="h-32 bg-slate-800/60 rounded-3xl mb-8"></div>
        <div className="h-64 bg-slate-800/40 rounded-3xl"></div>
      </div>
    );
  }

  const getRoleBadge = (role: MemberRole) => {
    switch (role) {
      case 'Admin':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      case 'Developer':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      default:
        return 'bg-gray-500/15 text-gray-300 border-gray-500/30';
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-2 text-xs font-semibold text-gray-400 hover:text-white mb-6 p-2 rounded-xl hover:bg-white/5 transition-colors cursor-pointer"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Quay lại danh sách Projects</span>
      </button>

      {/* Project Banner Header */}
      <div className="glass-panel rounded-3xl p-6 sm:p-8 mb-8 border border-white/10 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-80 bg-indigo-600/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {project.project_name}
              </h1>
              <span className="text-xs px-3 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-medium">
                ID #{project.id}
              </span>
            </div>
            <p className="text-sm text-gray-400 max-w-2xl">
              {project.description || 'Chưa có mô tả chi tiết cho project này.'}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={onOpenInviteModal}
              className="px-4 py-2.5 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer"
            >
              <UserPlus className="w-4 h-4" />
              <span>Mời thành viên</span>
            </button>

            <button
              onClick={onOpenAddRepoModal}
              className="gradient-btn text-white px-4 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-2 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Thêm Git Repo</span>
            </button>
          </div>
        </div>

        {/* Quick Stats Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/10 text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
              <GitBranch className="w-4 h-4" />
            </div>
            <div>
              <p className="text-gray-400">Repositories</p>
              <p className="text-sm font-bold text-white">{project.repositories.length} repos</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <p className="text-gray-400">Thành viên</p>
              <p className="text-sm font-bold text-white">{project.members.length} thành viên</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <p className="text-gray-400">Owner ID</p>
              <p className="text-sm font-bold text-white">User #{project.owner_id}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 text-cyan-400">
              <Clock className="w-4 h-4" />
            </div>
            <div>
              <p className="text-gray-400">Ngày tạo</p>
              <p className="text-sm font-bold text-white">{new Date(project.created_at).toLocaleDateString('vi-VN')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-white/10 mb-6">
        <button
          onClick={() => setActiveTab('repos')}
          className={`px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'repos'
              ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <GitBranch className="w-4 h-4" />
          <span>Git Repositories ({project.repositories.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('members')}
          className={`px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 transition-all flex items-center gap-2 cursor-pointer ${
            activeTab === 'members'
              ? 'border-purple-500 text-purple-400 bg-purple-500/5'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Thành viên ({project.members.length})</span>
        </button>
      </div>

      {/* Tab Content: Repositories */}
      {activeTab === 'repos' && (
        <div>
          {project.repositories.length === 0 ? (
            <div className="glass-panel rounded-3xl p-10 text-center border border-white/10">
              <GitBranch className="w-10 h-10 text-gray-500 mx-auto mb-3" />
              <h3 className="text-base font-bold text-white mb-1">Chưa đính kèm Repository nào</h3>
              <p className="text-xs text-gray-400 mb-5">
                Thêm link Git repository để chuẩn bị indexing dữ liệu mã nguồn
              </p>
              <button
                onClick={onOpenAddRepoModal}
                className="gradient-btn text-white px-4 py-2.5 rounded-xl text-xs font-semibold inline-flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                <span>Thêm Git Repo Mới</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {project.repositories.map((repo) => (
                <div
                  key={repo.id}
                  className="glass-card rounded-2xl p-5 border border-white/10 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-base">{repo.name}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-medium">
                          {repo.default_branch}
                        </span>
                      </div>

                      <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 font-semibold uppercase tracking-wider">
                        {repo.status}
                      </span>
                    </div>

                    <p className="text-xs text-gray-400 mb-3">
                      {repo.description || 'Không có mô tả cho repository này.'}
                    </p>

                    <a
                      href={repo.git_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-mono bg-slate-950/60 px-3 py-1.5 rounded-lg border border-white/5 max-w-full truncate"
                    >
                      <ExternalLink className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{repo.git_url}</span>
                    </a>
                  </div>

                  <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-[11px] text-gray-500">
                    <span>Đã tạo: {new Date(repo.created_at).toLocaleDateString('vi-VN')}</span>
                    <span className="text-xs text-gray-400">Indexing status: Pending</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab Content: Members */}
      {activeTab === 'members' && (
        <div>
          <div className="glass-panel rounded-3xl p-6 border border-white/10">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Users className="w-4 h-4 text-purple-400" />
                <span>Danh sách thành viên dự án</span>
              </h3>

              <button
                onClick={onOpenInviteModal}
                className="px-3.5 py-2 rounded-xl bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Mời thêm</span>
              </button>
            </div>

            <div className="divide-y divide-white/5">
              {project.members.map((member) => {
                const isOwner = member.user_id === project.owner_id;
                return (
                  <div key={member.id} className="py-3.5 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-purple-600/20 border border-purple-500/30 text-purple-300 flex items-center justify-center font-bold text-sm">
                        {member.user_username.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs sm:text-sm font-bold text-white">
                            {member.user_full_name || member.user_username}
                          </span>
                          {isOwner && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold">
                              Owner
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-400">{member.user_email}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className={`text-[11px] px-2.5 py-1 rounded-full border font-semibold ${getRoleBadge(member.role)}`}>
                        {member.role}
                      </span>

                      {!isOwner && (
                        <button
                          onClick={() => handleRemove(member.user_id)}
                          disabled={removingId === member.user_id}
                          className="p-2 rounded-lg text-gray-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer disabled:opacity-50"
                          title="Xóa khỏi project"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
