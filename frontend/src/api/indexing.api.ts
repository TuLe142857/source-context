import { http } from './http';
import type { IndexingJobResponse, TriggerBranchIndexingRequest } from './types/indexing';

/** Triggers indexing for every branch registered under the workspace. */
export function triggerWorkspaceIndexApi(workspaceId: number): Promise<IndexingJobResponse[]> {
  return http.post<IndexingJobResponse[]>(`/indexing/${workspaceId}`).then((res) => res.data);
}

/** Triggers indexing for a single branch, optionally at a specific commit. */
export function triggerBranchIndexApi(
  workspaceId: number,
  branchId: number,
  data?: TriggerBranchIndexingRequest
): Promise<IndexingJobResponse> {
  return http
    .post<IndexingJobResponse>(`/indexing/${workspaceId}/branch/${branchId}`, data)
    .then((res) => res.data);
}

export function listIndexingJobsApi(workspaceId: number): Promise<IndexingJobResponse[]> {
  return http.get<IndexingJobResponse[]>(`/indexing/${workspaceId}/jobs`).then((res) => res.data);
}
