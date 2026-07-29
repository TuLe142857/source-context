import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deleteBranchApi, triggerBranchIndexApi } from '@/api/branches.api';
import { updateBranchApi } from '@/api/branches.template';
import type { UpdateBranchRequest } from '@/api/types/templates';

const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;
const indexingJobsKey = (workspaceId: number) => ['workspaces', workspaceId, 'indexing-jobs'] as const;

export function useDeleteBranchMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (branchId: number) => deleteBranchApi(workspaceId, branchId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

export function useTriggerBranchIndexMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (branchId: number) => triggerBranchIndexApi(workspaceId, branchId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
      void queryClient.invalidateQueries({ queryKey: indexingJobsKey(workspaceId) });
    },
  });
}

/** Template only — no update-branch endpoint exists on the backend yet. */
export function useUpdateBranchMutation(workspaceId: number) {
  return useMutation({
    mutationFn: ({ branchId, data }: { branchId: number; data: UpdateBranchRequest }) =>
      updateBranchApi(workspaceId, branchId, data),
  });
}
