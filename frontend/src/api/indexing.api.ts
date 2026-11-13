import { http } from './http';
import type { IndexingJobResponse, IndexingRunResponse, IndexingStateResponse } from './types/indexing';

/** Triggers indexing for every branch registered under the workspace. */
export function triggerWorkspaceIndexApi(
  workspaceId: number,
  forceFull = false,
): Promise<IndexingJobResponse[]> {
  const query = forceFull ? '?force_full=true' : '';
  return http.post<IndexingJobResponse[]>(`/indexing/${workspaceId}${query}`).then((res) => res.data);
}

/** Triggers indexing for a single branch. Backend resolves the commit hash from git itself. */
export function triggerBranchIndexApi(
  workspaceId: number,
  branchId: number,
  forceFull = false,
): Promise<IndexingJobResponse> {
  const query = forceFull ? '?force_full=true' : '';
  return http
    .post<IndexingJobResponse>(`/indexing/${workspaceId}/branch/${branchId}${query}`)
    .then((res) => res.data);
}

export function listIndexingJobsApi(workspaceId: number): Promise<IndexingJobResponse[]> {
  return http.get<IndexingJobResponse[]>(`/indexing/${workspaceId}/jobs`).then((res) => res.data);
}

export function listIndexingRunsApi(workspaceId: number): Promise<IndexingRunResponse[]> {
  return http.get<IndexingRunResponse[]>(`/indexing/${workspaceId}/runs`).then((res) => res.data);
}

export function listIndexingStatesApi(workspaceId: number): Promise<IndexingStateResponse[]> {
  return http.get<IndexingStateResponse[]>(`/indexing/${workspaceId}/states`).then((res) => res.data);
}

export function getIndexingRunApi(workspaceId: number, runId: number): Promise<IndexingRunResponse> {
  return http.get<IndexingRunResponse>(`/indexing/${workspaceId}/runs/${runId}`).then((res) => res.data);
}
