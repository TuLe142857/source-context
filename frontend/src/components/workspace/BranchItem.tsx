import { useState, type FormEvent } from 'react';
import { toast } from 'sonner';
import { GitBranch, Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { TemplateBadge } from '@/components/TemplateBadge';
import { IndexingStatusBadge } from './IndexingStatusBadge';
import { ProjectItem } from './ProjectItem';
import { AddProjectDialog } from './AddProjectDialog';
import { useDeleteBranchMutation, useTriggerBranchIndexMutation, useUpdateBranchMutation } from '@/hooks/useBranches';
import type { BranchResponse } from '@/api/types/branch';
import { getErrorMessage } from '@/lib/errors';

export function BranchItem({ workspaceId, branch }: { workspaceId: number; branch: BranchResponse }) {
  const deleteMutation = useDeleteBranchMutation(workspaceId);
  const reindexMutation = useTriggerBranchIndexMutation(workspaceId);
  const updateMutation = useUpdateBranchMutation(workspaceId);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [addProjectOpen, setAddProjectOpen] = useState(false);
  const [reindexOpen, setReindexOpen] = useState(false);
  const [commitHashed, setCommitHashed] = useState('');

  const handleDelete = () => {
    deleteMutation.mutate(branch.id, {
      onSuccess: () => {
        toast.success(`Đã xoá branch "${branch.branch_name}".`);
        setConfirmOpen(false);
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  const handleReindex = (e: FormEvent) => {
    e.preventDefault();
    reindexMutation.mutate(
      { branchId: branch.id, commitHashed: commitHashed.trim() || undefined },
      {
        onSuccess: () => {
          toast.success(`Đã kích hoạt reindex cho branch "${branch.branch_name}".`);
          setReindexOpen(false);
          setCommitHashed('');
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  const handleEdit = () => {
    updateMutation.mutate(
      { branchId: branch.id, data: { commit_hashed: branch.commit_hashed } },
      { onError: (err) => toast.error(getErrorMessage(err)) }
    );
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
          <IndexingStatusBadge status={branch.indexing_status} />
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <TemplateBadge label="Sửa sắp có" />
          <Button
            variant="ghost"
            size="icon"
            title="Trigger reindex branch"
            onClick={() => setReindexOpen(true)}
            disabled={reindexMutation.isPending}
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
          <Button variant="ghost" size="icon" title="Sửa branch (template)" onClick={handleEdit}>
            <Pencil className="w-3.5 h-3.5" />
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

      <Dialog open={reindexOpen} onOpenChange={setReindexOpen}>
        <DialogContent>
          <form onSubmit={handleReindex}>
            <DialogHeader>
              <DialogTitle>Reindex branch "{branch.branch_name}"</DialogTitle>
              <DialogDescription>
                Để trống để reindex tại commit hiện tại đã đăng ký (
                <span className="font-mono">{branch.commit_hashed.slice(0, 12)}</span>), hoặc nhập commit hash
                khác để reindex tại commit đó.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-1.5 py-4">
              <Label htmlFor={`reindex-commit-${branch.id}`}>Commit hash (tuỳ chọn)</Label>
              <Input
                id={`reindex-commit-${branch.id}`}
                value={commitHashed}
                onChange={(e) => setCommitHashed(e.target.value)}
                placeholder={branch.commit_hashed}
                className="font-mono"
              />
            </div>
            <DialogFooter>
              <Button type="submit" disabled={reindexMutation.isPending}>
                {reindexMutation.isPending ? 'Đang kích hoạt…' : 'Reindex'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

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
