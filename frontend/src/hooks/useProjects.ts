import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProjectApi, deleteProjectApi, updateProjectApi } from '@/api/projects.api';
import { reindexProjectApi } from '@/api/projects.template';
import type { ProjectCreateRequest, ProjectUpdateRequest } from '@/api/types/project';

const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;

export function useCreateProjectMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ branchId, data }: { branchId: number; data: ProjectCreateRequest }) =>
      createProjectApi(workspaceId, branchId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

export function useDeleteProjectMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectId: number) => deleteProjectApi(workspaceId, projectId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

/** Promoted to real — PATCH /branches/{workspaceId}/projects/{projectId} now exists. */
export function useUpdateProjectMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: number; data: ProjectUpdateRequest }) =>
      updateProjectApi(workspaceId, projectId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

/** Template only — no per-project reindex endpoint exists on the backend yet. */
export function useReindexProjectMutation(workspaceId: number) {
  return useMutation({
    mutationFn: (projectId: number) => reindexProjectApi(workspaceId, projectId),
  });
}
