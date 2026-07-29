import { toast } from 'sonner';
import { Loader2, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { isJobInFlight, useIndexingJobsQuery, useTriggerWorkspaceIndexMutation } from '@/hooks/useIndexing';
import { formatDateTime } from '@/lib/format';
import { getErrorMessage } from '@/lib/errors';

export function IndexingPanel({ workspaceId }: { workspaceId: number }) {
  const jobsQuery = useIndexingJobsQuery(workspaceId);
  const triggerMutation = useTriggerWorkspaceIndexMutation(workspaceId);

  const handleTrigger = () => {
    triggerMutation.mutate(undefined, {
      onSuccess: (jobs) => toast.success(`Đã kích hoạt reindex cho ${jobs.length} branch.`),
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-foreground">Indexing Jobs</h3>
          <p className="text-xs text-muted-foreground mt-1">
            Chưa có webhook tự động — dùng nút này để trigger reindex thủ công cho toàn bộ workspace.
          </p>
        </div>
        <Button size="sm" onClick={handleTrigger} disabled={triggerMutation.isPending}>
          {triggerMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Reindex toàn bộ workspace
        </Button>
      </div>

      <div className="glass-card rounded-2xl border overflow-hidden">
        {jobsQuery.isLoading ? (
          <div className="p-6 space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : jobsQuery.data && jobsQuery.data.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job</TableHead>
                <TableHead>Branch ID</TableHead>
                <TableHead>Trạng thái</TableHead>
                <TableHead>Tiến độ</TableHead>
                <TableHead>Cập nhật</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {jobsQuery.data.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-mono text-xs">#{job.id}</TableCell>
                  <TableCell className="font-mono text-xs">#{job.branch_id}</TableCell>
                  <TableCell>
                    {job.error_message ? (
                      <Badge variant="destructive">{job.status}</Badge>
                    ) : (
                      <Badge className={isJobInFlight(job) ? 'bg-sky-500/15 text-sky-400 border-sky-500/30 animate-pulse' : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'}>
                        {job.status}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{job.progress_pct}%</TableCell>
                  <TableCell className="text-muted-foreground">{formatDateTime(job.updated_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <div className="p-10 text-center text-sm text-muted-foreground">
            Chưa có job lập chỉ mục nào. Nhấn "Reindex toàn bộ workspace" để bắt đầu.
          </div>
        )}
      </div>
    </div>
  );
}
