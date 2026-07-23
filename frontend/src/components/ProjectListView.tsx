import React, { useState } from 'react';
import type { Project } from '../types';
import { Plus, Search, FolderGit2, ArrowRight, Calendar, UserCheck } from 'lucide-react';

interface ProjectListViewProps {
  projects: Project[];
  isLoading: boolean;
  onSelectProject: (projectId: number) => void;
  onOpenCreateModal: () => void;
}

export const ProjectListView: React.FC<ProjectListViewProps> = ({
  projects,
  isLoading,
  onSelectProject,
  onOpenCreateModal,
}) => {
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filteredProjects = projects.filter((p) =>
    p.project_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <span>Danh Sách Projects</span>
            <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-semibold">
              {projects.length} Dự án
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Quản lý các không gian làm việc và tích hợp kho lưu trữ mã nguồn
          </p>
        </div>

        <button
          onClick={onOpenCreateModal}
          className="gradient-btn text-white px-5 py-3 rounded-2xl text-sm font-semibold flex items-center justify-center gap-2 cursor-pointer shadow-xl shadow-indigo-600/25"
        >
          <Plus className="w-5 h-5" />
          <span>Tạo Project Mới</span>
        </button>
      </div>

      {/* Search Filter Bar */}
      <div className="mb-8">
        <div className="relative max-w-md">
          <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Tìm kiếm project theo tên hoặc mô tả..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-slate-900/90 border border-white/10 rounded-2xl px-11 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all shadow-inner"
          />
        </div>
      </div>

      {/* Project Cards Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-panel rounded-3xl p-6 h-48 animate-pulse flex flex-col justify-between">
              <div className="space-y-3">
                <div className="h-5 bg-slate-800 rounded-lg w-2/3"></div>
                <div className="h-4 bg-slate-800/60 rounded-lg w-full"></div>
              </div>
              <div className="h-4 bg-slate-800/40 rounded-lg w-1/3"></div>
            </div>
          ))}
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="glass-panel rounded-3xl p-12 text-center border border-white/10 max-w-md mx-auto my-12">
          <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center mx-auto mb-4 border border-indigo-500/30">
            <FolderGit2 className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-bold text-white mb-1">Chưa tìm thấy Project nào</h3>
          <p className="text-xs text-gray-400 mb-6">
            {searchTerm ? 'Không tìm thấy kết quả phù hợp với từ khóa.' : 'Hãy khởi tạo project đầu tiên của bạn ngay!'}
          </p>
          {!searchTerm && (
            <button
              onClick={onOpenCreateModal}
              className="gradient-btn text-white px-5 py-2.5 rounded-xl text-xs font-semibold inline-flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              <span>Tạo Project Mới</span>
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => (
            <div
              key={project.id}
              onClick={() => onSelectProject(project.id)}
              className="glass-card rounded-3xl p-6 flex flex-col justify-between cursor-pointer group"
            >
              <div>
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="p-3 rounded-2xl bg-indigo-600/15 border border-indigo-500/20 text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-200">
                    <FolderGit2 className="w-6 h-6" />
                  </div>
                  <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium flex items-center gap-1">
                    <UserCheck className="w-3 h-3" /> Owner #{project.owner_id}
                  </span>
                </div>

                <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-1 mb-1.5">
                  {project.project_name}
                </h3>
                <p className="text-xs text-gray-400 line-clamp-2 min-h-[2rem]">
                  {project.description || 'Chưa có mô tả chi tiết cho project này.'}
                </p>
              </div>

              <div className="pt-4 border-t border-white/10 flex items-center justify-between mt-4">
                <div className="flex items-center gap-1.5 text-[11px] text-gray-500">
                  <Calendar className="w-3.5 h-3.5" />
                  <span>{new Date(project.created_at).toLocaleDateString('vi-VN')}</span>
                </div>

                <span className="text-xs font-semibold text-indigo-400 group-hover:translate-x-1 transition-transform flex items-center gap-1">
                  <span>Chi tiết</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
