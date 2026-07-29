import { http } from './http';
import type { IndexingJobResponse } from './types/indexing';

/** Triggers indexing for every branch registered under the workspace. */
export function triggerWorkspaceIndexApi(workspaceId: number): Promise<IndexingJobResponse[]> {
  return http.post<IndexingJobResponse[]>(`/workspaces/${workspaceId}/index`).then((res) => res.data);
}

export function listIndexingJobsApi(workspaceId: number): Promise<IndexingJobResponse[]> {
  return http.get<IndexingJobResponse[]>(`/workspaces/${workspaceId}/indexing-jobs`).then((res) => res.data);
}
