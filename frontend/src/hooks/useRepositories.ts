import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createRepositoryApi, deleteRepositoryApi, inspectGitHubBranchesApi } from '@/api/repositories.api';
import type { InspectGitHubBranchesRequest, RepositoryCreateRequest } from '@/api/types/repository';

const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;

export function useInspectBranchesMutation() {
  return useMutation({
    mutationFn: ({ workspaceId, data }: { workspaceId: number; data: InspectGitHubBranchesRequest }) =>
      inspectGitHubBranchesApi(workspaceId, data),
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
