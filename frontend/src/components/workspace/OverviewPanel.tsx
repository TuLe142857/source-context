import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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
import { useSession } from '@/hooks/useAuth';
import { useDeleteWorkspaceMutation, useUpdateWorkspaceMutation } from '@/hooks/useWorkspaces';
import type { WorkspaceResponse } from '@/api/types/workspace';
import { getErrorMessage } from '@/lib/errors';

export function OverviewPanel({ workspace }: { workspace: WorkspaceResponse }) {
  const { user } = useSession();
  const navigate = useNavigate();
  const updateMutation = useUpdateWorkspaceMutation(workspace.id);
  const deleteMutation = useDeleteWorkspaceMutation();

  const [name, setName] = useState(workspace.workspace_name);
  const [description, setDescription] = useState(workspace.description ?? '');
  const [deleteOpen, setDeleteOpen] = useState(false);

  const isOwner = user?.id === workspace.owner_id;

  const handleSave = (e: FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(
      { workspace_name: name, description },
      {
        onSuccess: () => toast.success('Đã cập nhật workspace.'),
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  const handleDelete = () => {
    deleteMutation.mutate(workspace.id, {
      onSuccess: () => {
        toast.success(`Đã xoá workspace "${workspace.workspace_name}".`);
        navigate('/workspaces', { replace: true });
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  return (
    <div className="space-y-6 max-w-lg">
      <div className="flex items-center gap-2">
        <h3 className="font-semibold text-foreground">Thông tin workspace</h3>
        {isOwner && <TemplateBadge />}
      </div>
      <form onSubmit={handleSave} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="ws-overview-name">Tên workspace</Label>
          <Input
            id="ws-overview-name"
            required
            disabled={!isOwner}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ws-overview-desc">Mô tả</Label>
          <Textarea
            id="ws-overview-desc"
            disabled={!isOwner}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Mô tả ngắn về workspace này"
          />
        </div>
        {isOwner && (
          <Button type="submit" disabled={updateMutation.isPending}>
            {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Lưu thay đổi'}
          </Button>
        )}
      </form>

      {isOwner && (
        <div className="rounded-2xl border border-destructive/30 bg-destructive/5 p-4 space-y-3">
          <div>
            <h4 className="text-sm font-semibold text-destructive">Vùng nguy hiểm</h4>
            <p className="text-xs text-muted-foreground mt-1">
              Xoá workspace sẽ xoá toàn bộ repository, branch, sub-project và thành viên bên trong.
            </p>
          </div>
          <Button variant="destructive" size="sm" onClick={() => setDeleteOpen(true)}>
            <Trash2 className="w-3.5 h-3.5" /> Xoá workspace
          </Button>
        </div>
      )}

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xoá workspace "{workspace.workspace_name}"?</AlertDialogTitle>
            <AlertDialogDescription>Hành động này không thể hoàn tác.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Huỷ</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleteMutation.isPending}>
              Xoá vĩnh viễn
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
