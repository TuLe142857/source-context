import { http } from './http';
import type { IndexingJobResponse } from './types/indexing';

/** Triggers indexing for every branch registered under the workspace. */
export function triggerWorkspaceIndexApi(workspaceId: number): Promise<IndexingJobResponse[]> {
  return http.post<IndexingJobResponse[]>(`/indexing/${workspaceId}`).then((res) => res.data);
}

/** Triggers indexing for a single branch. Backend resolves the commit hash from git itself. */
export function triggerBranchIndexApi(workspaceId: number, branchId: number): Promise<IndexingJobResponse> {
  return http
    .post<IndexingJobResponse>(`/indexing/${workspaceId}/branch/${branchId}`)
    .then((res) => res.data);
}

export function listIndexingJobsApi(workspaceId: number): Promise<IndexingJobResponse[]> {
  return http.get<IndexingJobResponse[]>(`/indexing/${workspaceId}/jobs`).then((res) => res.data);
}
