import { http } from './http';
import type {
  InspectGitHubBranchesRequest,
  RemoteBranchesResponse,
  RepositoryCreateRequest,
  RepositoryResponse,
} from './types/repository';

/** Preview branches through the GitHub App installation linked to this workspace. */
export function inspectGitHubBranchesApi(
  workspaceId: number,
  data: InspectGitHubBranchesRequest
): Promise<RemoteBranchesResponse> {
  return http.post<RemoteBranchesResponse>(`/branches/${workspaceId}/remote-branches`, data).then((res) => res.data);
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
