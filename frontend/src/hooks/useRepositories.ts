import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createRepositoryApi, deleteRepositoryApi, inspectGitHubBranchesApi } from '@/api/repositories.api';
import { addBranchToRepositoryApi, updateRepositoryApi } from '@/api/repositories.template';
import type { InspectGitHubBranchesRequest, RepositoryCreateRequest } from '@/api/types/repository';
import type { BranchCreateRequest } from '@/api/types/branch';
import type { UpdateRepositoryRequest } from '@/api/types/templates';

const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;

/** Standalone GitHub utility now — no longer scoped to a workspace. */
export function useInspectBranchesMutation() {
  return useMutation({
    mutationFn: (data: InspectGitHubBranchesRequest) => inspectGitHubBranchesApi(data),
  });
}

export function useCreateRepositoryMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RepositoryCreateRequest) => createRepositoryApi(workspaceId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

export function useDeleteRepositoryMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (repositoryId: number) => deleteRepositoryApi(workspaceId, repositoryId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

/** Template only — no update-repository endpoint exists on the backend yet. */
export function useUpdateRepositoryMutation(workspaceId: number) {
  return useMutation({
    mutationFn: ({ repositoryId, data }: { repositoryId: number; data: UpdateRepositoryRequest }) =>
      updateRepositoryApi(workspaceId, repositoryId, data),
  });
}

/** Template only — no add-branch-to-existing-repository endpoint exists on the backend yet. */
export function useAddBranchToRepositoryMutation(workspaceId: number) {
  return useMutation({
    mutationFn: ({ repositoryId, data }: { repositoryId: number; data: BranchCreateRequest }) =>
      addBranchToRepositoryApi(workspaceId, repositoryId, data),
  });
}
