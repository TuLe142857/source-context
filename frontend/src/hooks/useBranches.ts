import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { deleteBranchApi, listWorkspaceBranchesApi } from '@/api/branches.api';
import { triggerBranchIndexApi } from '@/api/indexing.api';
import { updateBranchApi } from '@/api/branches.template';
import type { UpdateBranchRequest } from '@/api/types/templates';

const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;
const indexingJobsKey = (workspaceId: number) => ['workspaces', workspaceId, 'indexing-jobs'] as const;
const workspaceBranchesKey = (workspaceId: number, repositoryId?: number) =>
  ['workspaces', workspaceId, 'branches', repositoryId ?? null] as const;

export function useDeleteBranchMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (branchId: number) => deleteBranchApi(workspaceId, branchId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

/** Optional commit_hashed override, per TriggerBranchIndexingRequest. */
export function useTriggerBranchIndexMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ branchId, commitHashed }: { branchId: number; commitHashed?: string }) =>
      triggerBranchIndexApi(
        workspaceId,
        branchId,
        commitHashed ? { commit_hashed: commitHashed } : undefined
      ),
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

/** Flat, workspace-scoped branch list — GET /branches/{workspaceId}/workspace-branches. */
export function useWorkspaceBranchesQuery(workspaceId: number, repositoryId?: number) {
  return useQuery({
    queryKey: workspaceBranchesKey(workspaceId, repositoryId),
    queryFn: () => listWorkspaceBranchesApi(workspaceId, repositoryId ? { repository_id: repositoryId } : undefined),
    enabled: Number.isFinite(workspaceId),
  });
}
