import { toast } from 'sonner';
import { Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useIndexingRunsQuery,
  useIndexingStatesQuery,
  useTriggerWorkspaceIndexMutation,
} from '@/hooks/useIndexing';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage } from '@/lib/errors';
import type { IndexingStateResponse } from '@/api/types/indexing';

export function IndexingPanel({ workspaceId }: { workspaceId: number }) {
  const runsQuery = useIndexingRunsQuery(workspaceId);
  const statesQuery = useIndexingStatesQuery(workspaceId);
  const triggerMutation = useTriggerWorkspaceIndexMutation(workspaceId);
  const statesByBranch = new Map<number, IndexingStateResponse>(
    (statesQuery.data ?? []).map((state) => [state.branch_id, state]),
  );

  const handleTrigger = (forceFull = false) => {
    if (
      forceFull &&
      !window.confirm('Bắt đầu full reindex cho tất cả branch trong workspace? Thao tác này sẽ tạo lại graph và vectors.')
    ) {
      return;
    }
    triggerMutation.mutate(forceFull, {
      onSuccess: (jobs) => toast.success(`Đã tạo ${jobs.length} yêu cầu indexing.`),
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-foreground">Indexing Jobs</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Yêu cầu indexing cho các branch trong workspace. Backend quyết định cách xử lý.
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" onClick={() => handleTrigger()} disabled={triggerMutation.isPending}>
            {triggerMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            Index workspace
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => handleTrigger(true)}
            disabled={triggerMutation.isPending}
          >
            Full reindex
          </Button>
        </div>
      </div>

      <div className="glass-card rounded-2xl border overflow-hidden">
        {runsQuery.isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : runsQuery.data && runsQuery.data.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run / Job</TableHead>
                <TableHead>Branch ID</TableHead>
                <TableHead>Checkpoint</TableHead>
                <TableHead>Mode</TableHead>
                <TableHead>Commit</TableHead>
                <TableHead>Changes (A/M/D/R)</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead>Stage</TableHead>
                <TableHead>Thời gian</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runsQuery.data.map((run) => (
                <TableRow key={run.id}>
                  <TableCell className="font-mono text-xs">#{run.id}{run.job_id ? ` / #${run.job_id}` : ''}</TableCell>
                  <TableCell className="font-mono text-xs">#{run.branch_id}</TableCell>
                  <TableCell
                    className="text-xs"
                    title={`Latest observed: ${statesByBranch.get(run.branch_id)?.latest_observed_commit_sha ?? '—'} · Index version: ${statesByBranch.get(run.branch_id)?.index_version ?? '—'} · Checkpoint valid: ${statesByBranch.get(run.branch_id)?.checkpoint_valid ?? false}`}
                  >
                    <div>{statesByBranch.get(run.branch_id)?.status ?? 'UNINDEXED'}</div>
                    <div className="font-mono text-muted-foreground">
                      {statesByBranch.get(run.branch_id)?.indexed_commit_sha
                        ? `${statesByBranch.get(run.branch_id)?.indexed_commit_sha?.slice(0, 10)} · ${statesByBranch.get(run.branch_id)?.checkpoint_valid ? 'valid' : 'needs rebuild'}`
                        : 'No checkpoint'}
                    </div>
                  </TableCell>
                  <TableCell title={run.fallback_reason ?? undefined}>
                    <div>{run.mode}</div>
                    {run.fallback_reason && (
                      <div className="max-w-48 text-xs text-amber-500">{run.fallback_reason}</div>
                    )}
                  </TableCell>
                  <TableCell className="font-mono text-xs" title={`Base: ${run.base_commit_sha ?? '—'} → Target: ${run.target_commit_sha}`}>
                    {(run.base_commit_sha?.slice(0, 7) ?? '—')} → {run.target_commit_sha.slice(0, 7)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {run.statistics
                      ? `${run.statistics.added_files ?? 0}/${run.statistics.modified_files ?? 0}/${run.statistics.deleted_files ?? 0}/${run.statistics.renamed_files ?? 0} · ${run.statistics.processed_files ?? 0} processed`
                      : '—'}
                  </TableCell>
                  <TableCell>
                    <div>
                      <Badge
                        className={
                          run.status === 'FAILED' || run.error_message
                            ? 'bg-destructive/15 text-destructive border-destructive/30'
                            : ['PENDING', 'QUEUED', 'RUNNING', 'RETRYING', 'RECOVERING'].includes(run.status)
                              ? 'bg-sky-500/15 text-sky-400 border-sky-500/30 animate-pulse'
                              : run.status === 'COMPLETED'
                                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                                : 'bg-muted text-muted-foreground border-muted'
                        }
                      >
                        {run.status}
                      </Badge>
                      {run.error_message && (
                        <p className="mt-1 max-w-64 text-xs text-destructive">{run.error_message}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{run.current_stage ?? '—'}</TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(run.completed_at ?? run.started_at ?? run.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="p-10 text-center text-sm text-muted-foreground">
            Chưa có job lập chỉ mục nào. Nhấn "Index workspace" để bắt đầu.
          </div>
        )}
      </div>
    </div>
  );
}
