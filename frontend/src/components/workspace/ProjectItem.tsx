import { useState } from 'react';
import { toast } from 'sonner';
import { FolderCode, Pencil, RefreshCw, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
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
import { EditProjectDialog } from './EditProjectDialog';
import { useDeleteProjectMutation, useReindexProjectMutation } from '@/hooks/useProjects';
import type { ProjectResponse } from '@/api/types/project';
import { getErrorMessage } from '@/lib/errors';

export function ProjectItem({ workspaceId, project }: { workspaceId: number; project: ProjectResponse }) {
  const deleteMutation = useDeleteProjectMutation(workspaceId);
  const reindexMutation = useReindexProjectMutation(workspaceId);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);

  const handleDelete = () => {
    deleteMutation.mutate(project.id, {
      onSuccess: () => {
        toast.success(`Đã xoá sub-project "${project.root_dir}".`);
        setConfirmOpen(false);
      },
      onError: (err) => toast.error(getErrorMessage(err)),
    });
  };

  const handleReindex = () => {
    reindexMutation.mutate(project.id, { onError: (err) => toast.error(getErrorMessage(err)) });
  };

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border/60 bg-background/40 px-3 py-2">
      <div className="flex items-center gap-2 min-w-0">
        <FolderCode className="w-4 h-4 text-cyan-400 shrink-0" />
        <span className="text-sm text-foreground font-mono truncate">{project.root_dir}</span>
        <Badge variant="outline" className="text-xs">
          {project.language}
        </Badge>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <TemplateBadge label="Reindex sắp có" />
        <Button variant="ghost" size="icon" title="Reindex sub-project (template)" onClick={handleReindex}>
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
        <Button variant="ghost" size="icon" title="Sửa sub-project" onClick={() => setEditOpen(true)}>
          <Pencil className="w-3.5 h-3.5" />
        </Button>
        <Button variant="ghost" size="icon" title="Xoá sub-project" onClick={() => setConfirmOpen(true)}>
          <Trash2 className="w-3.5 h-3.5 text-destructive" />
        </Button>
      </div>

      <EditProjectDialog workspaceId={workspaceId} project={project} open={editOpen} onOpenChange={setEditOpen} />

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Xoá sub-project "{project.root_dir}"?</AlertDialogTitle>
            <AlertDialogDescription>Hành động này không thể hoàn tác.</AlertDialogDescription>
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
