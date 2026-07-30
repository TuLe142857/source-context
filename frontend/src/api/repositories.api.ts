import { http } from './http';
import type {
  InspectGitHubBranchesRequest,
  RemoteBranchesResponse,
  RepositoryCreateRequest,
  RepositoryResponse,
} from './types/repository';

/** Standalone GitHub utility — no longer scoped to a workspace. */
export function inspectGitHubBranchesApi(data: InspectGitHubBranchesRequest): Promise<RemoteBranchesResponse> {
  return http.post<RemoteBranchesResponse>('/branches/remote-branches', data).then((res) => res.data);
}

export function createRepositoryApi(
  workspaceId: number,
  data: RepositoryCreateRequest
): Promise<RepositoryResponse> {
  return http.post<RepositoryResponse>(`/branches/${workspaceId}/repositories`, data).then((res) => res.data);
}

export function deleteRepositoryApi(workspaceId: number, repositoryId: number): Promise<void> {
  return http.delete(`/branches/${workspaceId}/repositories/${repositoryId}`).then(() => undefined);
}
