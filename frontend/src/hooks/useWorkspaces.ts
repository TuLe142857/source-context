import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  addWorkspaceMemberApi,
  createWorkspaceApi,
  deleteWorkspaceApi,
  getWorkspaceApi,
  getWorkspaceHierarchyApi,
  listWorkspaceMembersApi,
  listWorkspacesApi,
  removeMemberApi,
} from '@/api/workspaces.api';
import type { AddMemberRequest, CreateWorkspaceRequest } from '@/api/types/workspace';

const WORKSPACES_KEY = ['workspaces'] as const;
const workspaceKey = (workspaceId: number) => ['workspaces', workspaceId] as const;
const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;
const workspaceMembersKey = (workspaceId: number) => ['workspaces', workspaceId, 'members'] as const;

export function useWorkspacesQuery() {
  return useQuery({ queryKey: WORKSPACES_KEY, queryFn: () => listWorkspacesApi() });
}

/**
 * WorkspaceHierarchyResponse omits `description` — fetch the plain
 * WorkspaceResponse alongside it whenever the description is needed (e.g.
 * the Overview tab).
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

/**
 * `WorkspaceHierarchyResponse.members` currently comes back empty from
 * `GET /branches/{id}/hierarchy` (observed backend inconsistency after the
 * Round 2 router move) — the dedicated `GET /workspaces/{id}/members`
 * endpoint returns correct data (including the owner), so the Members tab
 * sources from here instead of the hierarchy response.
 */
export function useWorkspaceMembersQuery(workspaceId: number) {
  return useQuery({
    queryKey: workspaceMembersKey(workspaceId),
    queryFn: () => listWorkspaceMembersApi(workspaceId),
    enabled: Number.isFinite(workspaceId),
  });
}

export function useCreateWorkspaceMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateWorkspaceRequest) => createWorkspaceApi(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: WORKSPACES_KEY });
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
      void queryClient.invalidateQueries({ queryKey: workspaceMembersKey(workspaceId) });
    },
  });
}

/** Promoted to real — DELETE /workspaces/{id}/members/{userId} now exists. */
export function useRemoveMemberMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => removeMemberApi(workspaceId, userId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
      void queryClient.invalidateQueries({ queryKey: workspaceMembersKey(workspaceId) });
    },
  });
}
