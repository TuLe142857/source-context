import { http } from './http';
import type { ProjectCreateRequest, ProjectResponse } from './types/project';

export function createProjectApi(
  workspaceId: number,
  branchId: number,
  data: ProjectCreateRequest
): Promise<ProjectResponse> {
  return http
    .post<ProjectResponse>(`/workspaces/${workspaceId}/branches/${branchId}/projects`, data)
    .then((res) => res.data);
}

export function deleteProjectApi(workspaceId: number, projectId: number): Promise<void> {
  return http.delete(`/workspaces/${workspaceId}/projects/${projectId}`).then(() => undefined);
}
