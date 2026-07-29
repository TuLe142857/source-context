import { http } from './http';
import type { IndexingJobResponse } from './types/indexing';

export function deleteBranchApi(workspaceId: number, branchId: number): Promise<void> {
  return http.delete(`/workspaces/${workspaceId}/branches/${branchId}`).then(() => undefined);
}

/** Triggers indexing for a single branch (all its sub-projects). */
export function triggerBranchIndexApi(workspaceId: number, branchId: number): Promise<IndexingJobResponse> {
  return http
    .post<IndexingJobResponse>(`/workspaces/${workspaceId}/branches/${branchId}/index`)
    .then((res) => res.data);
}
