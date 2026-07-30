import { notImplemented } from './template';
import type { WorkspaceResponse } from './types/workspace';
import type { UpdateWorkspaceRequest } from './types/templates';

/** Self action for a non-owner member — no such endpoint exists in the backend spec yet. */
export function leaveWorkspaceApi(_workspaceId: number): Promise<void> {
  return notImplemented('Rời khỏi workspace');
}

/** Backend removed PATCH /workspaces/{id} — demoted from real to template. */
export function updateWorkspaceApi(
  _workspaceId: number,
  _data: UpdateWorkspaceRequest
): Promise<WorkspaceResponse> {
  return notImplemented('Cập nhật tên/mô tả workspace');
}
