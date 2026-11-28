import { useState, useEffect, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { FolderKanban, Loader2, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import { linkGitHubInstallation } from '@/api/webhooks.api';
import { useCreateWorkspaceMutation, useWorkspacesQuery } from '@/hooks/useWorkspaces';
import { getErrorMessage } from '@/lib/errors';

export function WorkspaceListPage() {
  const workspacesQuery = useWorkspacesQuery();
  const createMutation = useCreateWorkspaceMutation();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();

  useEffect(() => {
    const pendingInstallationId = searchParams.get('pending_installation_id');
    if (pendingInstallationId) {
      linkGitHubInstallation({ installation_id: Number(pendingInstallationId) })
        .then(() => {
          toast.success('Liên kết tài khoản với GitHub App thành công!');
          queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
        })
        .catch((err) => {
          toast.error('Không thể liên kết GitHub App: ' + getErrorMessage(err));
        })
        .finally(() => {
          setSearchParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              next.delete('pending_installation_id');
              next.delete('setup_action');
              return next;
            },
            { replace: true }
          );
        });
      return;
    }

    if (searchParams.get('github_connected') === 'true') {
      toast.success('Liên kết tài khoản với GitHub App thành công!');
      queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete('github_connected');
          return next;
        },
        { replace: true }
      );
    }
  }, [searchParams, setSearchParams, queryClient]);

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const handleCreate = (e: FormEvent) => {
    e.preventDefault();
    createMutation.mutate(
      { workspace_name: name, description: description || undefined },
      {
        onSuccess: () => {
          toast.success(`Đã tạo workspace "${name}".`);
          setCreateOpen(false);
          setName('');
          setDescription('');
        },
        onError: (err) => toast.error(getErrorMessage(err)),
      }
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Workspaces</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Nơi cấu hình repository, branch và sub-project để lập chỉ mục mã nguồn.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="w-4 h-4" /> Tạo workspace
        </Button>
      </div>

      {workspacesQuery.isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 rounded-2xl" />
          ))}
        </div>
      ) : workspacesQuery.data && workspacesQuery.data.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {workspacesQuery.data.map((ws) => (
            <Link
              key={ws.id}
              to={`/workspaces/${ws.id}`}
              className="glass-card rounded-2xl p-5 border block"
            >
              <div className="flex items-start gap-3">
                <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 shrink-0">
                  <FolderKanban className="w-5 h-5 text-white" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-foreground truncate">{ws.workspace_name}</h3>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {ws.description || 'Không có mô tả'}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="glass-panel rounded-2xl p-12 text-center border">
          <FolderKanban className="w-10 h-10 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground">
            Chưa có workspace nào. Tạo workspace đầu tiên để bắt đầu.
          </p>
        </div>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <form onSubmit={handleCreate}>
            <DialogHeader>
              <DialogTitle>Tạo workspace mới</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-1.5">
                <Label htmlFor="ws-name">Tên workspace</Label>
                <Input
                  id="ws-name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My Team Workspace"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ws-desc">Mô tả</Label>
                <Textarea
                  id="ws-desc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Mô tả ngắn về workspace này"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Tạo workspace'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
