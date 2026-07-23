export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string | null;
  created_at: string;
}

export type MemberRole = 'Admin' | 'Developer' | 'Viewer';

export interface Member {
  id: number;
  project_id: number;
  user_id: number;
  role: MemberRole;
  user_email: string;
  user_username: string;
  user_full_name?: string | null;
  created_at: string;
}

export interface RepositoryLink {
  id: number;
  project_id: number;
  name: string;
  git_url: string;
  description?: string | null;
  default_branch: string;
  status: string;
  created_at: string;
}

export interface Project {
  id: number;
  project_name: string;
  description?: string | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail extends Project {
  members: Member[];
  repositories: RepositoryLink[];
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}
