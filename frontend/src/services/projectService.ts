import { fetchApi } from './api';
import type { Project, ProjectDetail, Member, RepositoryLink, MemberRole } from '../types';

export async function getProjectsApi(): Promise<Project[]> {
  return fetchApi<Project[]>('/projects/');
}

export async function createProjectApi(data: {
  project_name: string;
  description?: string;
}): Promise<Project> {
  return fetchApi<Project>('/projects/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getProjectDetailApi(projectId: number): Promise<ProjectDetail> {
  return fetchApi<ProjectDetail>(`/projects/${projectId}`);
}

export async function updateProjectApi(
  projectId: number,
  data: { project_name?: string; description?: string }
): Promise<Project> {
  return fetchApi<Project>(`/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function inviteMemberApi(
  projectId: number,
  data: { email: string; role: MemberRole }
): Promise<Member> {
  return fetchApi<Member>(`/projects/${projectId}/members/invite`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function removeMemberApi(
  projectId: number,
  userId: number
): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(`/projects/${projectId}/members/${userId}`, {
    method: 'DELETE',
  });
}

export async function linkRepositoryApi(
  projectId: number,
  data: {
    name: string;
    git_url: string;
    description?: string;
    default_branch?: string;
  }
): Promise<RepositoryLink> {
  return fetchApi<RepositoryLink>(`/projects/${projectId}/repositories`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}
