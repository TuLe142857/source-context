import { http } from './http';
import type { BranchResponse } from './types/branch';

export function deleteBranchApi(workspaceId: number, branchId: number): Promise<void> {
  return http.delete(`/branches/${workspaceId}/${branchId}`).then(() => undefined);
}

/** Flat list of a workspace's branches, optionally filtered by repository. */
export function listWorkspaceBranchesApi(
  workspaceId: number,
  params?: { repository_id?: number }
): Promise<BranchResponse[]> {
  return http
    .get<BranchResponse[]>(`/branches/${workspaceId}/workspace-branches`, { params })
    .then((res) => res.data);
}
