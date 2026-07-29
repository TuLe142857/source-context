import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createProjectApi, deleteProjectApi } from '@/api/projects.api';
import { reindexProjectApi, updateProjectApi } from '@/api/projects.template';
import type { ProjectCreateRequest } from '@/api/types/project';
import type { UpdateProjectRequest } from '@/api/types/templates';

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

/** Template only — no update-project endpoint exists on the backend yet. */
export function useUpdateProjectMutation(workspaceId: number) {
  return useMutation({
    mutationFn: ({ projectId, data }: { projectId: number; data: UpdateProjectRequest }) =>
      updateProjectApi(workspaceId, projectId, data),
  });
}

/** Template only — no per-project reindex endpoint exists on the backend yet. */
export function useReindexProjectMutation(workspaceId: number) {
  return useMutation({
    mutationFn: (projectId: number) => reindexProjectApi(workspaceId, projectId),
  });
}
