import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  addWorkspaceMemberApi,
  createWorkspaceApi,
  deleteWorkspaceApi,
  getWorkspaceApi,
  getWorkspaceHierarchyApi,
  listWorkspacesApi,
  updateWorkspaceApi,
} from '@/api/workspaces.api';
import { leaveWorkspaceApi, removeMemberApi } from '@/api/workspaces.template';
import type { AddMemberRequest, WorkspaceCreate, WorkspaceUpdate } from '@/api/types/workspace';

const WORKSPACES_KEY = ['workspaces'] as const;
const workspaceKey = (workspaceId: number) => ['workspaces', workspaceId] as const;
const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;

export function useWorkspacesQuery() {
  return useQuery({ queryKey: WORKSPACES_KEY, queryFn: () => listWorkspacesApi() });
}

/**
 * WorkspaceHierarchyResponse omits `description` — fetch the plain
 * WorkspaceResponse alongside it whenever the description is needed (e.g.
 * the Overview tab's edit form).
 */
export function useWorkspaceQuery(workspaceId: number) {
  return useQuery({
    queryKey: workspaceKey(workspaceId),
    queryFn: () => getWorkspaceApi(workspaceId),
    enabled: Number.isFinite(workspaceId),
  });
}

export function useWorkspaceHierarchyQuery(workspaceId: number) {
  return useQuery({
    queryKey: workspaceHierarchyKey(workspaceId),
    queryFn: () => getWorkspaceHierarchyApi(workspaceId),
    enabled: Number.isFinite(workspaceId),
  });
}

export function useCreateWorkspaceMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkspaceCreate) => createWorkspaceApi(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: WORKSPACES_KEY });
    },
  });
}

export function useUpdateWorkspaceMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: WorkspaceUpdate) => updateWorkspaceApi(workspaceId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: WORKSPACES_KEY });
      void queryClient.invalidateQueries({ queryKey: workspaceKey(workspaceId) });
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

export function useDeleteWorkspaceMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (workspaceId: number) => deleteWorkspaceApi(workspaceId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: WORKSPACES_KEY });
    },
  });
}

export function useAddMemberMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AddMemberRequest) => addWorkspaceMemberApi(workspaceId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
    },
  });
}

/** Template only — no DELETE-member endpoint exists on the backend yet. */
export function useRemoveMemberMutation(workspaceId: number) {
  return useMutation({
    mutationFn: (userId: number) => removeMemberApi(workspaceId, userId),
  });
}

/** Template only — no leave-workspace endpoint exists on the backend yet. */
export function useLeaveWorkspaceMutation() {
  return useMutation({
    mutationFn: (workspaceId: number) => leaveWorkspaceApi(workspaceId),
  });
}
