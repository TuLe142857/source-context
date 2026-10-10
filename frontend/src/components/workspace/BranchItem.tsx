import { useState } from 'react';
import { toast } from 'sonner';
import { GitBranch, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { IndexingStatusBadge } from './IndexingStatusBadge';
import { ProjectItem } from './ProjectItem';
import { AddProjectDialog } from './AddProjectDialog';
import { useDeleteBranchMutation, useTriggerBranchIndexMutation } from '@/hooks/useBranches';
import type { BranchResponse } from '@/api/types/branch';
import { getErrorMessage } from '@/lib/errors';

export function BranchItem({ workspaceId, branch }: { workspaceId: number; branch: BranchResponse }) {
  const deleteMutation = useDeleteBranchMutation(workspaceId);
  const reindexMutation = useTriggerBranchIndexMutation(workspaceId);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [addProjectOpen, setAddProjectOpen] = useState(false);

  const handleDelete = () => {
    deleteMutation.mutate(branch.id, {
      onSuccess: () => {
        toast.success(`Đã xoá branch "${branch.branch_name}".`);
        setConfirmOpen(false);
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  const handleReindex = () => {
    reindexMutation.mutate(branch.id, {
      onSuccess: () => toast.success(`Đã kích hoạt reindex cho branch "${branch.branch_name}".`),
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  return (
    <div className="rounded-xl border border-border bg-card/40 p-3 space-y-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2 min-w-0">
          <GitBranch className="w-4 h-4 text-indigo-400 shrink-0" />
          <span className="text-sm font-semibold text-foreground truncate">{branch.branch_name}</span>
          <span className="text-xs text-muted-foreground font-mono truncate">
            @{branch.commit_hashed.slice(0, 12)}
          </span>
          {branch.indexed_commit_sha && branch.indexed_commit_sha !== branch.commit_hashed && (
            <span className="text-xs text-amber-400" title={`Commit đã index: ${branch.indexed_commit_sha}`}>
              (đã index @{branch.indexed_commit_sha.slice(0, 12)})
            </span>
          )}
          <IndexingStatusBadge status={branch.indexing_status} />
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            title="Trigger reindex branch"
            onClick={handleReindex}
            disabled={reindexMutation.isPending}
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
          <Button variant="ghost" size="icon" title="Xoá branch" onClick={() => setConfirmOpen(true)}>
            <Trash2 className="w-3.5 h-3.5 text-destructive" />
          </Button>
        </div>
      </div>

      <div className="pl-6 space-y-2">
        {branch.projects.length > 0 ? (
          branch.projects.map((project) => (
            <ProjectItem key={project.id} workspaceId={workspaceId} project={project} />
          ))
        ) : (
          <p className="text-xs text-muted-foreground">Chưa có sub-project nào được cấu hình.</p>
        )}
        <Button variant="outline" size="sm" onClick={() => setAddProjectOpen(true)}>
          <Plus className="w-3.5 h-3.5" /> Thêm sub-project
        </Button>
      </div>

      <AddProjectDialog
        workspaceId={workspaceId}
        branchId={branch.id}
        open={addProjectOpen}
        onOpenChange={setAddProjectOpen}
      />

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xoá branch "{branch.branch_name}"?</AlertDialogTitle>
            <AlertDialogDescription>
              Toàn bộ sub-project cấu hình dưới branch này cũng sẽ bị xoá. Hành động này không thể hoàn tác.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleteMutation.isPending}>
              Xoá
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
