import { http } from './http';
import type {
  AddMemberRequest,
  MemberResponse,
  WorkspaceCreate,
  WorkspaceHierarchyResponse,
  WorkspaceResponse,
  WorkspaceUpdate,
} from './types/workspace';

export function listWorkspacesApi(params?: { skip?: number; limit?: number }): Promise<WorkspaceResponse[]> {
  return http.get<WorkspaceResponse[]>('/workspaces', { params }).then((res) => res.data);
}

export function createWorkspaceApi(data: WorkspaceCreate): Promise<WorkspaceResponse> {
  return http.post<WorkspaceResponse>('/workspaces', data).then((res) => res.data);
}

export function getWorkspaceApi(workspaceId: number): Promise<WorkspaceResponse> {
  return http.get<WorkspaceResponse>(`/workspaces/${workspaceId}`).then((res) => res.data);
}

export function updateWorkspaceApi(workspaceId: number, data: WorkspaceUpdate): Promise<WorkspaceResponse> {
  return http.patch<WorkspaceResponse>(`/workspaces/${workspaceId}`, data).then((res) => res.data);
}

export function deleteWorkspaceApi(workspaceId: number): Promise<void> {
  return http.delete(`/workspaces/${workspaceId}`).then(() => undefined);
}

export function getWorkspaceHierarchyApi(workspaceId: number): Promise<WorkspaceHierarchyResponse> {
  return http.get<WorkspaceHierarchyResponse>(`/workspaces/${workspaceId}/hierarchy`).then((res) => res.data);
}

export function addWorkspaceMemberApi(workspaceId: number, data: AddMemberRequest): Promise<MemberResponse> {
  return http.post<MemberResponse>(`/workspaces/${workspaceId}/members`, data).then((res) => res.data);
}

export function listWorkspaceMembersApi(workspaceId: number): Promise<MemberResponse[]> {
  return http.get<MemberResponse[]>(`/workspaces/${workspaceId}/members`).then((res) => res.data);
}
