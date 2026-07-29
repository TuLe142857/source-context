import { notImplemented } from './template';

/** Owner action — no DELETE-member endpoint exists in the backend spec yet. */
export function removeMemberApi(_workspaceId: number, _userId: number): Promise<void> {
  return notImplemented('Xoá thành viên khỏi workspace');
}

/** Self action for a non-owner member — no such endpoint exists in the backend spec yet. */
export function leaveWorkspaceApi(_workspaceId: number): Promise<void> {
  return notImplemented('Rời khỏi workspace');
}
