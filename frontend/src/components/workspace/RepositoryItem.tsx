import { useState } from 'react';
import { toast } from 'sonner';
import { GitFork, Pencil, Plus, Trash2 } from 'lucide-react';
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
import { TemplateBadge } from '@/components/TemplateBadge';
import { BranchItem } from './BranchItem';
import { AddBranchToRepositoryDialog } from './AddBranchToRepositoryDialog';
import { useDeleteRepositoryMutation, useUpdateRepositoryMutation } from '@/hooks/useRepositories';
import type { RepositoryResponse } from '@/api/types/repository';
import { getErrorMessage } from '@/lib/errors';

export function RepositoryItem({
  workspaceId,
  repository,
}: {
  workspaceId: number;
  repository: RepositoryResponse;
}) {
  const deleteMutation = useDeleteRepositoryMutation(workspaceId);
  const updateMutation = useUpdateRepositoryMutation(workspaceId);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [addBranchOpen, setAddBranchOpen] = useState(false);

  const handleDelete = () => {
    deleteMutation.mutate(repository.id, {
      onSuccess: () => {
        toast.success(`Đã xoá repository "${repository.name}".`);
        setConfirmOpen(false);
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  const handleEdit = () => {
    updateMutation.mutate(
      { repositoryId: repository.id, data: { name: repository.name } },
      { onError: (err) => toast.error(getErrorMessage(err)) }
    );
  };

  return (
    <div className="glass-card rounded-2xl border p-4 space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-start gap-3 min-w-0">
          <div className="p-2 rounded-lg bg-cyan-500/15 border border-cyan-500/30 shrink-0">
            <GitFork className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="min-w-0">
            <h4 className="font-semibold text-foreground truncate">{repository.name}</h4>
            <p className="text-xs text-muted-foreground truncate font-mono">{repository.git_url}</p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <TemplateBadge label="Sửa sắp có" />
          <Button variant="ghost" size="icon" title="Sửa repository (template)" onClick={handleEdit}>
            <Pencil className="w-3.5 h-3.5" />
          </Button>
          <Button variant="ghost" size="icon" title="Xoá repository" onClick={() => setConfirmOpen(true)}>
            <Trash2 className="w-3.5 h-3.5 text-destructive" />
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {repository.branches.length > 0 ? (
          repository.branches.map((branch) => (
            <BranchItem key={branch.id} workspaceId={workspaceId} branch={branch} />
          ))
        ) : (
          <p className="text-xs text-muted-foreground">Chưa có branch nào được đăng ký.</p>
        )}
        <Button variant="outline" size="sm" onClick={() => setAddBranchOpen(true)}>
          <Plus className="w-3.5 h-3.5" /> Thêm branch vào repo này
          <TemplateBadge />
        </Button>
      </div>

      <AddBranchToRepositoryDialog
        workspaceId={workspaceId}
        repositoryId={repository.id}
        open={addBranchOpen}
        onOpenChange={setAddBranchOpen}
      />

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xoá repository "{repository.name}"?</AlertDialogTitle>
            <AlertDialogDescription>
              Toàn bộ branch và sub-project bên trong repository này cũng sẽ bị xoá. Hành động này
              không thể hoàn tác.
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
