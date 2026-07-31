import { notImplemented } from './template';
import type { RepositoryResponse } from './types/repository';
import type { BranchResponse } from './types/branch';
import type { BranchCreateRequest } from './types/branch';
import type { UpdateRepositoryRequest } from './types/templates';

/** No PATCH/PUT endpoint for Repository exists in the backend spec yet — create+delete only. */
export function updateRepositoryApi(
  _workspaceId: number,
  _repositoryId: number,
  _data: UpdateRepositoryRequest
): Promise<RepositoryResponse> {
  return notImplemented('Cập nhật thông tin repository');
}

/** No endpoint to register a branch on an already-existing repository — only at repo creation time. */
export function addBranchToRepositoryApi(
  _workspaceId: number,
  _repositoryId: number,
  _data: BranchCreateRequest
): Promise<BranchResponse> {
  return notImplemented('Thêm branch vào repository đã tồn tại');
}
