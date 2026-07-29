import { http } from './http';
import type {
  InspectGitHubBranchesRequest,
  RemoteBranchesResponse,
  RepositoryCreateRequest,
  RepositoryResponse,
} from './types/repository';

export function inspectGitHubBranchesApi(
  workspaceId: number,
  data: InspectGitHubBranchesRequest
): Promise<RemoteBranchesResponse> {
  return http
    .post<RemoteBranchesResponse>(`/workspaces/${workspaceId}/repositories/inspect-branches`, data)
    .then((res) => res.data);
}

export function createRepositoryApi(
  workspaceId: number,
  data: RepositoryCreateRequest
): Promise<RepositoryResponse> {
  return http
    .post<RepositoryResponse>(`/workspaces/${workspaceId}/repositories`, data)
    .then((res) => res.data);
}

export function deleteRepositoryApi(workspaceId: number, repositoryId: number): Promise<void> {
  return http.delete(`/workspaces/${workspaceId}/repositories/${repositoryId}`).then(() => undefined);
}
