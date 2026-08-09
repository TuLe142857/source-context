import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { deleteBranchApi, listWorkspaceBranchesApi } from '@/api/branches.api';
import { triggerBranchIndexApi } from '@/api/indexing.api';

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

/** Backend resolves the commit hash from git itself — no override needed. */
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

/** Flat, workspace-scoped branch list — GET /branches/{workspaceId}/workspace-branches. */
export function useWorkspaceBranchesQuery(workspaceId: number, repositoryId?: number) {
  return useQuery({
    queryKey: workspaceBranchesKey(workspaceId, repositoryId),
    queryFn: () => listWorkspaceBranchesApi(workspaceId, repositoryId ? { repository_id: repositoryId } : undefined),
    enabled: Number.isFinite(workspaceId),
  });
}
