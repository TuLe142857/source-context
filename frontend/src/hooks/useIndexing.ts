import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  listIndexingJobsApi,
  listIndexingRunsApi,
  listIndexingStatesApi,
  triggerWorkspaceIndexApi,
} from '@/api/indexing.api';
import type { IndexingJobResponse, IndexingRunResponse, IndexingStateResponse } from '@/api/types/indexing';

const workspaceHierarchyKey = (workspaceId: number) => ['workspaces', workspaceId, 'hierarchy'] as const;
const indexingJobsKey = (workspaceId: number) => ['workspaces', workspaceId, 'indexing-jobs'] as const;
const indexingRunsKey = (workspaceId: number) => ['workspaces', workspaceId, 'indexing-runs'] as const;
const indexingStatesKey = (workspaceId: number) => ['workspaces', workspaceId, 'indexing-states'] as const;

/**
 * status is a free string on the backend (not tied to BranchIndexingStatus),
 * so "in flight" is inferred from progress_pct/error_message rather than
 * matching specific status strings.
 */
export function isJobInFlight(job: IndexingJobResponse): boolean {
  return job.progress_pct < 100 && !job.error_message;
}

export function useIndexingJobsQuery(workspaceId: number) {
  return useQuery({
    queryKey: indexingJobsKey(workspaceId),
    queryFn: () => listIndexingJobsApi(workspaceId),
    enabled: Number.isFinite(workspaceId),
    refetchInterval: (query) => (query.state.data?.some(isJobInFlight) ? 3000 : false),
  });
}

export function useIndexingRunsQuery(workspaceId: number) {
  return useQuery<IndexingRunResponse[]>({
    queryKey: indexingRunsKey(workspaceId),
    queryFn: () => listIndexingRunsApi(workspaceId),
    enabled: Number.isFinite(workspaceId),
    refetchInterval: (query) =>
      query.state.data?.some((run) => ['PENDING', 'QUEUED', 'RUNNING', 'RETRYING', 'RECOVERING'].includes(run.status))
        ? 3000
        : false,
  });
}

export function useIndexingStatesQuery(workspaceId: number) {
  return useQuery<IndexingStateResponse[]>({
    queryKey: indexingStatesKey(workspaceId),
    queryFn: () => listIndexingStatesApi(workspaceId),
    enabled: Number.isFinite(workspaceId),
    refetchInterval: (query) =>
      query.state.data?.some((state) => state.status === 'INDEXING') ? 3000 : false,
  });
}

export function useTriggerWorkspaceIndexMutation(workspaceId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (forceFull: boolean) => triggerWorkspaceIndexApi(workspaceId, forceFull),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: workspaceHierarchyKey(workspaceId) });
      void queryClient.invalidateQueries({ queryKey: indexingJobsKey(workspaceId) });
      void queryClient.invalidateQueries({ queryKey: indexingRunsKey(workspaceId) });
      void queryClient.invalidateQueries({ queryKey: indexingStatesKey(workspaceId) });
    },
  });
}
