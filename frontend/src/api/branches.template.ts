import { notImplemented } from './template';
import type { BranchResponse } from './types/branch';
import type { UpdateBranchRequest } from './types/templates';

/** No PATCH/PUT endpoint for Branch exists in the backend spec yet — create+delete only. */
export function updateBranchApi(
  _workspaceId: number,
  _branchId: number,
  _data: UpdateBranchRequest
): Promise<BranchResponse> {
  return notImplemented('Cập nhật commit/branch');
}
