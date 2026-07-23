import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { AuthView } from './components/AuthView';
import { ProjectListView } from './components/ProjectListView';
import { ProjectDetailView } from './components/ProjectDetailView';
import { CreateProjectModal } from './components/CreateProjectModal';
import { InviteMemberModal } from './components/InviteMemberModal';
import { AddRepoModal } from './components/AddRepoModal';
import type { Project, ProjectDetail, MemberRole } from './types';
import {
  getProjectsApi,
  createProjectApi,
  getProjectDetailApi,
  inviteMemberApi,
  removeMemberApi,
  linkRepositoryApi,
} from './services/projectService';
import './App.css';

const MainApp: React.FC = () => {
  const { isAuthenticated, isLoading: isAuthLoading } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectDetail | null>(null);
  const [isProjectsLoading, setIsProjectsLoading] = useState<boolean>(false);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);

  // Modal states
  const [isCreateModalOpen, setIsCreateModalOpen] = useState<boolean>(false);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState<boolean>(false);
  const [isAddRepoModalOpen, setIsAddRepoModalOpen] = useState<boolean>(false);

  // Toast Feedback State
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Load project list when authenticated
  const loadProjects = async () => {
    setIsProjectsLoading(true);
    try {
      const data = await getProjectsApi();
      setProjects(data);
    } catch (err: any) {
      showToast(err.message || 'Không thể tải danh sách projects', 'error');
    } finally {
      setIsProjectsLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadProjects();
    } else {
      setProjects([]);
      setSelectedProject(null);
    }
  }, [isAuthenticated]);

  // Select & load project detail
  const handleSelectProject = async (projectId: number) => {
    setIsDetailLoading(true);
    try {
      const detail = await getProjectDetailApi(projectId);
      setSelectedProject(detail);
    } catch (err: any) {
      showToast(err.message || 'Không thể tải chi tiết project', 'error');
    } finally {
      setIsDetailLoading(false);
    }
  };

  // Create Project
  const handleCreateProject = async (name: string, description?: string) => {
    const newProj = await createProjectApi({ project_name: name, description });
    showToast(`Tạo thành công project "${newProj.project_name}"!`);
    await loadProjects();
    await handleSelectProject(newProj.id);
  };

  // Invite Member
  const handleInviteMember = async (email: string, role: MemberRole) => {
    if (!selectedProject) return;
    const newMember = await inviteMemberApi(selectedProject.id, { email, role });
    showToast(`Đã gửi lời mời tham gia tới ${newMember.user_email}!`);
    await handleSelectProject(selectedProject.id);
  };

  // Remove Member
  const handleRemoveMember = async (userId: number) => {
    if (!selectedProject) return;
    await removeMemberApi(selectedProject.id, userId);
    showToast('Đã xóa thành viên khỏi project.');
    await handleSelectProject(selectedProject.id);
  };

  // Link Repository
  const handleLinkRepository = async (data: {
    name: string;
    git_url: string;
    description?: string;
    default_branch?: string;
  }) => {
    if (!selectedProject) return;
    const newRepo = await linkRepositoryApi(selectedProject.id, data);
    showToast(`Đã liên kết Git Repository "${newRepo.name}" thành công!`);
    await handleSelectProject(selectedProject.id);
  };

  if (isAuthLoading) {
    return (
      <div className="min-h-screen bg-[#07090e] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin"></div>
          <p className="text-xs text-gray-400 font-medium">Đang tải ứng dụng...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthView />;
  }

  return (
    <div className="min-h-screen bg-[#07090e] text-gray-100 flex flex-col">
      <Navbar onGoHome={() => setSelectedProject(null)} />

      {/* Toast Notification */}
      {toast && (
        <div
          className={`fixed bottom-6 right-6 z-50 px-5 py-3.5 rounded-2xl shadow-2xl border text-xs font-semibold flex items-center gap-2 animate-bounce-slow ${
            toast.type === 'success'
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 backdrop-blur-md'
              : 'bg-rose-500/15 border-rose-500/30 text-rose-300 backdrop-blur-md'
          }`}
        >
          <span>{toast.message}</span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="flex-1">
        {selectedProject ? (
          <ProjectDetailView
            project={selectedProject}
            isLoading={isDetailLoading}
            onBack={() => setSelectedProject(null)}
            onOpenInviteModal={() => setIsInviteModalOpen(true)}
            onOpenAddRepoModal={() => setIsAddRepoModalOpen(true)}
            onRemoveMember={handleRemoveMember}
          />
        ) : (
          <ProjectListView
            projects={projects}
            isLoading={isProjectsLoading}
            onSelectProject={handleSelectProject}
            onOpenCreateModal={() => setIsCreateModalOpen(true)}
          />
        )}
      </main>

      {/* Modals */}
      <CreateProjectModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateProject}
      />

      <InviteMemberModal
        isOpen={isInviteModalOpen}
        onClose={() => setIsInviteModalOpen(false)}
        onInvite={handleInviteMember}
      />

      <AddRepoModal
        isOpen={isAddRepoModalOpen}
        onClose={() => setIsAddRepoModalOpen(false)}
        onAdd={handleLinkRepository}
      />
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
