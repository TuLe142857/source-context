import { http } from './http';
import type { ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest } from './types/project';

export function createProjectApi(
  workspaceId: number,
  branchId: number,
  data: ProjectCreateRequest
): Promise<ProjectResponse> {
  return http.post<ProjectResponse>(`/branches/${workspaceId}/${branchId}/projects`, data).then((res) => res.data);
}

/** PATCH now exists on the backend (promoted from template). */
export function updateProjectApi(
  workspaceId: number,
  projectId: number,
  data: ProjectUpdateRequest
): Promise<ProjectResponse> {
  return http
    .patch<ProjectResponse>(`/branches/${workspaceId}/projects/${projectId}`, data)
    .then((res) => res.data);
}

export function deleteProjectApi(workspaceId: number, projectId: number): Promise<void> {
  return http.delete(`/branches/${workspaceId}/projects/${projectId}`).then(() => undefined);
}
